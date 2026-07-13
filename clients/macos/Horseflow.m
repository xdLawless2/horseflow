#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <AVFoundation/AVFoundation.h>

static NSURL *HorseflowAPIURL;
static const CGKeyCode SpaceKey = 49;
static const CGKeyCode LeftCommandKey = 55;
static const CGKeyCode RightCommandKey = 54;
static const CGKeyCode PasteKey = 9;
static const int64_t SyntheticEventMarker = 0x484F525345;

static void HFLog(NSString *message) {
    NSISO8601DateFormatter *formatter = NSISO8601DateFormatter.new;
    fprintf(stderr, "[%s] %s\n",
            [[formatter stringFromDate:NSDate.date] UTF8String],
            message.UTF8String);
}

static void HFNotify(NSString *message) {
    NSTask *task = NSTask.new;
    task.launchPath = @"/usr/bin/osascript";
    task.arguments = @[
        @"-e", @"on run argv",
        @"-e", @"display notification (item 1 of argv) with title \"Horseflow\"",
        @"-e", @"end run",
        @"--", message
    ];
    [task launch];
}

static void HFPaste(NSString *text) {
    NSPasteboard *pasteboard = NSPasteboard.generalPasteboard;
    [pasteboard clearContents];
    [pasteboard setString:text forType:NSPasteboardTypeString];

    CGEventSourceRef source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    if (!source) {
        HFLog(@"failed to create paste event source");
        return;
    }

    CGEventRef down = CGEventCreateKeyboardEvent(source, PasteKey, true);
    CGEventRef up = CGEventCreateKeyboardEvent(source, PasteKey, false);
    if (down && up) {
        CGEventSetFlags(down, kCGEventFlagMaskCommand);
        CGEventSetFlags(up, kCGEventFlagMaskCommand);
        CGEventSetIntegerValueField(
            down, kCGEventSourceUserData, SyntheticEventMarker
        );
        CGEventSetIntegerValueField(
            up, kCGEventSourceUserData, SyntheticEventMarker
        );
        CGEventPost(kCGHIDEventTap, down);
        CGEventPost(kCGHIDEventTap, up);
    } else {
        HFLog(@"failed to create paste events");
    }

    if (down) CFRelease(down);
    if (up) CFRelease(up);
    CFRelease(source);
}

@interface HFRecorder : NSObject
@property(nonatomic, strong) AVAudioEngine *engine;
@property(nonatomic, strong) AVAudioFile *file;
@property(nonatomic, strong) NSURL *recordingURL;
@property(nonatomic) BOOL recording;
@property(nonatomic) BOOL finishing;
- (void)start;
- (void)abort;
- (void)finish;
@end

@implementation HFRecorder

- (instancetype)init {
    self = [super init];
    if (self) _engine = AVAudioEngine.new;
    return self;
}

- (void)start {
    if (self.recording || self.finishing) return;

    AVAudioInputNode *input = self.engine.inputNode;
    AVAudioFormat *format = [input outputFormatForBus:0];
    if (format.channelCount == 0) {
        HFNotify(@"No microphone input is available");
        return;
    }

    NSURL *directory = [[NSURL fileURLWithPath:NSTemporaryDirectory()
                                   isDirectory:YES]
        URLByAppendingPathComponent:@"horseflow"
        isDirectory:YES];
    NSError *error = nil;
    [NSFileManager.defaultManager createDirectoryAtURL:directory
                            withIntermediateDirectories:YES
                                             attributes:nil
                                                  error:&error];
    if (error) {
        HFLog([NSString stringWithFormat:@"cannot create audio directory: %@", error]);
        return;
    }

    NSString *name = [NSString stringWithFormat:@"recording-%@.wav",
                      NSUUID.UUID.UUIDString];
    NSURL *url = [directory URLByAppendingPathComponent:name];
    self.file = [[AVAudioFile alloc] initForWriting:url
                                           settings:format.settings
                                              error:&error];
    if (!self.file) {
        HFLog([NSString stringWithFormat:@"cannot create recording: %@", error]);
        HFNotify(@"Could not start recording");
        return;
    }

    self.recordingURL = url;
    __weak HFRecorder *weakSelf = self;
    [input installTapOnBus:0
                bufferSize:1024
                    format:format
                     block:^(AVAudioPCMBuffer *buffer, AVAudioTime *when) {
        HFRecorder *strongSelf = weakSelf;
        if (!strongSelf.file) return;
        NSError *writeError = nil;
        if (![strongSelf.file writeFromBuffer:buffer error:&writeError]) {
            HFLog([NSString stringWithFormat:@"audio write failed: %@", writeError]);
        }
    }];

    [self.engine prepare];
    if (![self.engine startAndReturnError:&error]) {
        [input removeTapOnBus:0];
        self.file = nil;
        self.recordingURL = nil;
        [NSFileManager.defaultManager removeItemAtURL:url error:nil];
        HFLog([NSString stringWithFormat:@"audio engine failed: %@", error]);
        HFNotify(@"Could not start recording");
        return;
    }

    self.recording = YES;
    HFLog(@"recording started");
}

- (void)stopEngine {
    if (self.recording) {
        [self.engine.inputNode removeTapOnBus:0];
        [self.engine stop];
        [self.engine reset];
    }
    self.file = nil;
    self.recording = NO;
}

- (void)abort {
    if (!self.recording || self.finishing) return;
    NSURL *url = self.recordingURL;
    [self stopEngine];
    self.recordingURL = nil;
    if (url) [NSFileManager.defaultManager removeItemAtURL:url error:nil];
    HFLog(@"speculative recording discarded");
}

- (void)finish {
    if (!self.recording || self.finishing || !self.recordingURL) return;
    self.finishing = YES;
    NSURL *url = self.recordingURL;
    dispatch_after(
        dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.3 * NSEC_PER_SEC)),
        dispatch_get_main_queue(),
        ^{
            [self stopEngine];
            self.recordingURL = nil;
            [self upload:url];
        }
    );
}

- (void)upload:(NSURL *)url {
    NSError *error = nil;
    NSData *audio = [NSData dataWithContentsOfURL:url options:0 error:&error];
    if (!audio) {
        self.finishing = NO;
        [NSFileManager.defaultManager removeItemAtURL:url error:nil];
        HFLog([NSString stringWithFormat:@"cannot read recording: %@", error]);
        HFNotify(@"Could not read the recording");
        return;
    }

    NSString *boundary = [NSString stringWithFormat:@"Horseflow-%@",
                          NSUUID.UUID.UUIDString];
    NSMutableData *body = NSMutableData.data;
    [body appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary]
        dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[
        @"Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n"
        dataUsingEncoding:NSUTF8StringEncoding
    ]];
    [body appendData:[@"Content-Type: audio/wav\r\n\r\n"
        dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:audio];
    [body appendData:[[NSString stringWithFormat:@"\r\n--%@--\r\n", boundary]
        dataUsingEncoding:NSUTF8StringEncoding]];

    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:HorseflowAPIURL];
    request.HTTPMethod = @"POST";
    request.timeoutInterval = 120;
    request.HTTPBody = body;
    [request setValue:[NSString stringWithFormat:
                       @"multipart/form-data; boundary=%@", boundary]
   forHTTPHeaderField:@"Content-Type"];

    NSURLSessionDataTask *task = [
        NSURLSession.sharedSession
        dataTaskWithRequest:request
        completionHandler:^(NSData *data, NSURLResponse *response,
                            NSError *requestError) {
            [NSFileManager.defaultManager removeItemAtURL:url error:nil];
            dispatch_async(dispatch_get_main_queue(), ^{
                self.finishing = NO;
            });

            if (requestError) {
                HFLog([NSString stringWithFormat:@"upload failed: %@", requestError]);
                HFNotify(@"Transcription request failed");
                return;
            }

            NSInteger status = [(NSHTTPURLResponse *)response statusCode];
            NSDictionary *json = data
                ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil]
                : nil;
            NSString *text = [json[@"text"] isKindOfClass:NSString.class]
                ? json[@"text"] : nil;
            if (status != 200 || !text) {
                HFLog(@"invalid response from Horseflow");
                HFNotify(@"Horseflow returned an invalid response");
                return;
            }

            NSString *cleaned = [text
                stringByTrimmingCharactersInSet:
                    NSCharacterSet.whitespaceAndNewlineCharacterSet];
            dispatch_async(dispatch_get_main_queue(), ^{
                if (cleaned.length == 0) {
                    HFNotify(@"(nothing heard)");
                } else {
                    HFPaste(cleaned);
                    HFNotify(cleaned);
                }
            });
        }
    ];
    [task resume];
}

@end

@interface HFShortcutController : NSObject
@property(nonatomic, strong) HFRecorder *recorder;
@property(nonatomic) BOOL leftCommandDown;
@property(nonatomic) BOOL rightCommandDown;
@property(nonatomic) BOOL speculative;
@property(nonatomic) BOOL pushToTalk;
@property(nonatomic) BOOL swallowingSpace;
@property(nonatomic) CFMachPortRef eventTap;
@property(nonatomic) CFRunLoopSourceRef runLoopSource;
- (void)start;
- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event;
@end

static CGEventRef HFEventCallback(CGEventTapProxy proxy, CGEventType type,
                                  CGEventRef event, void *userInfo) {
    HFShortcutController *controller =
        (__bridge HFShortcutController *)userInfo;
    return [controller handleType:type event:event];
}

@implementation HFShortcutController

- (instancetype)init {
    self = [super init];
    if (self) _recorder = HFRecorder.new;
    return self;
}

- (BOOL)commandDown {
    return self.leftCommandDown || self.rightCommandDown;
}

- (void)start {
    NSDictionary *options = @{
        (__bridge NSString *)kAXTrustedCheckOptionPrompt: @YES
    };
    AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)options);
    if (!CGPreflightListenEventAccess()) CGRequestListenEventAccess();
    [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio
                            completionHandler:^(BOOL granted) {
        HFLog(granted ? @"microphone permission granted"
                      : @"microphone permission denied");
    }];
    [self installEventTapOrRetry];
}

- (void)installEventTapOrRetry {
    if (self.eventTap) return;

    CGEventMask mask =
        CGEventMaskBit(kCGEventKeyDown)
        | CGEventMaskBit(kCGEventKeyUp)
        | CGEventMaskBit(kCGEventFlagsChanged);
    self.eventTap = CGEventTapCreate(
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionDefault,
        mask,
        HFEventCallback,
        (__bridge void *)self
    );

    if (!self.eventTap) {
        HFLog(@"event tap unavailable; waiting for permissions");
        dispatch_after(
            dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC),
            dispatch_get_main_queue(),
            ^{ [self installEventTapOrRetry]; }
        );
        return;
    }

    self.runLoopSource = CFMachPortCreateRunLoopSource(
        kCFAllocatorDefault, self.eventTap, 0
    );
    CFRunLoopAddSource(
        CFRunLoopGetMain(), self.runLoopSource, kCFRunLoopCommonModes
    );
    CGEventTapEnable(self.eventTap, true);
    HFLog(@"Command+Space listener active");
}

- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event {
    if (CGEventGetIntegerValueField(event, kCGEventSourceUserData)
        == SyntheticEventMarker) {
        return event;
    }

    if (type == kCGEventTapDisabledByTimeout
        || type == kCGEventTapDisabledByUserInput) {
        if (self.eventTap) CGEventTapEnable(self.eventTap, true);
        return event;
    }

    CGKeyCode key = (CGKeyCode)CGEventGetIntegerValueField(
        event, kCGKeyboardEventKeycode
    );

    if (type == kCGEventFlagsChanged
        && (key == LeftCommandKey || key == RightCommandKey)) {
        BOOL isDown = (CGEventGetFlags(event) & kCGEventFlagMaskCommand) != 0;
        BOOL wasDown = self.commandDown;
        if (key == LeftCommandKey) {
            self.leftCommandDown = isDown;
        } else {
            self.rightCommandDown = isDown;
        }

        if (!wasDown && self.commandDown) {
            self.speculative = YES;
            [self.recorder start];
        } else if (wasDown && !self.commandDown) {
            if (self.pushToTalk) {
                self.pushToTalk = NO;
                [self.recorder finish];
            } else if (self.speculative) {
                [self.recorder abort];
            }
            self.speculative = NO;
        }
        return event;
    }

    if (key == SpaceKey) {
        if (type == kCGEventKeyDown && self.commandDown) {
            CGEventFlags extraModifiers =
                CGEventGetFlags(event)
                & (kCGEventFlagMaskShift
                   | kCGEventFlagMaskControl
                   | kCGEventFlagMaskAlternate);
            if (extraModifiers != 0) {
                if (self.speculative) {
                    self.speculative = NO;
                    [self.recorder abort];
                }
                return event;
            }

            self.swallowingSpace = YES;
            if (!self.pushToTalk) {
                if (!self.speculative && !self.recorder.recording) {
                    [self.recorder start];
                }
                self.speculative = NO;
                self.pushToTalk = YES;
            }
            return NULL;
        }

        if (self.swallowingSpace) {
            if (type == kCGEventKeyUp) {
                self.swallowingSpace = NO;
                if (self.pushToTalk) {
                    self.pushToTalk = NO;
                    [self.recorder finish];
                }
            }
            return NULL;
        }
    }

    if (type == kCGEventKeyDown && self.speculative
        && !self.pushToTalk) {
        self.speculative = NO;
        [self.recorder abort];
    }
    return event;
}

- (void)dealloc {
    if (_runLoopSource) {
        CFRunLoopRemoveSource(
            CFRunLoopGetMain(), _runLoopSource, kCFRunLoopCommonModes
        );
        CFRelease(_runLoopSource);
    }
    if (_eventTap) CFRelease(_eventTap);
}

@end

@interface HFAppDelegate : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) HFShortcutController *shortcutController;
@end

@implementation HFAppDelegate
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSString *configPath = [
        [NSHomeDirectory()
            stringByAppendingPathComponent:@"Library/Application Support/Horseflow"]
        stringByAppendingPathComponent:@"config.plist"
    ];
    NSDictionary *config = [NSDictionary dictionaryWithContentsOfFile:configPath];
    NSString *apiURL = config[@"APIURL"];
    if (![apiURL isKindOfClass:NSString.class] || apiURL.length == 0) {
        HFLog([NSString stringWithFormat:@"missing APIURL in %@", configPath]);
        HFNotify(@"Configuration is missing APIURL");
        [NSApp terminate:nil];
        return;
    }

    HorseflowAPIURL = [NSURL URLWithString:apiURL];
    self.shortcutController = HFShortcutController.new;
    [self.shortcutController start];
}
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        HFAppDelegate *delegate = HFAppDelegate.new;
        app.delegate = delegate;
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app run];
    }
    return 0;
}

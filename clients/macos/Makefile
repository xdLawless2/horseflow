APP := build/Horseflow.app
EXECUTABLE := $(APP)/Contents/MacOS/Horseflow

.PHONY: build clean

build: $(EXECUTABLE)

$(EXECUTABLE): Horseflow.m Info.plist
	mkdir -p "$(APP)/Contents/MacOS"
	clang -fobjc-arc -O2 \
		-framework Cocoa \
		-framework ApplicationServices \
		-framework AVFoundation \
		-o "$(EXECUTABLE)" Horseflow.m
	cp Info.plist "$(APP)/Contents/Info.plist"
	codesign --force --deep --sign - "$(APP)"

clean:
	rm -rf build

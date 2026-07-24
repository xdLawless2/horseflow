# JC(2) degree-(72,108) certificate replay

This directory contains a base64-split `tar.xz` archive of three exact Singular scripts. Reconstruct it with:

```bash
cat certs.b64.* | base64 -d > certs.tar.xz
echo '17a6e1522930a1ea4da025ec48299fd00bb5ca9a1150514213971a75f6b77e54  certs.tar.xz' | sha256sum -c -
mkdir certs && tar -xJf certs.tar.xz -C certs
```

Pinned scripts:

```text
ad032eb334b677ec9ead615f17e23194ea675fd42db8d806bee568217c9bd301  certificate_1_3.sing
6c6daa815089e3465f683cdb3979284c2f0fcd1bb1c44bec341fe56485ecb5ab  certificate_2_5.sing
b939e475a03e7b22fbfe6efb07cdf90738ea0f25490138c112342d8692bfd50f  certificate_3_7.sing
```

Each script evaluates a fully explicit characteristic-zero Bézout identity in `Q(theta)[z,p,q,h,k]` and exits nonzero unless the corresponding branch prints `UNIT_CERTIFICATE_VERIFIED` with no `FAILURE` marker.

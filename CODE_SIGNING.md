# Code Signing Policy

This policy describes how official Larevixo Windows releases are identified and how users can check their origin and integrity.

## Current release status

The repository's current Windows build and installer workflows do not sign `Larevixo.exe` or `Larevixo-Setup-<version>.exe`. Treat files from those workflows as **unsigned**. Windows may show an unknown-publisher or SmartScreen warning. Do not interpret the product name, file name, download location, or installer metadata as proof of a valid digital signature.

## Policy for official signed releases

When AvazTek publishes signed Windows releases, it will:

- Sign both the portable executable and the installer with an Authenticode code-signing certificate whose verified publisher identity is AvazTek.
- Use a trusted certificate authority and a secure signing service or protected signing environment. Private keys and signing credentials must not be committed to the repository, included in build artifacts, or exposed in workflow logs.
- Restrict signing access to authorized release maintainers, sign only reviewed release builds, and use a trusted timestamp so signatures can remain verifiable after the signing certificate expires.
- Verify each signature and its publisher identity before publishing the corresponding release. If a signature cannot be verified, that file must not be described as signed or published as an official signed release.
- Publish signed release files through AvazTek's official Larevixo release channels. Where checksums are published, users should obtain them from the same official release record and compare them before running a file.

## Verifying a Windows download

In PowerShell, check a downloaded executable or installer with:

```powershell
Get-AuthenticodeSignature .\Larevixo.exe | Format-List Status, StatusMessage, SignerCertificate
Get-ChildItem .\Larevixo-Setup-*.exe | ForEach-Object {
    Get-AuthenticodeSignature $_.FullName | Format-List Status, StatusMessage, SignerCertificate
}
```

For a signed official release, the status should be `Valid` and the signer certificate should identify AvazTek. A missing signature (`NotSigned`), an invalid status, or a different signer means the file does not meet this policy. Check the release announcement if the displayed status differs from what that release claims.

## Reporting a signing concern

If an official release has an unexpected, invalid, or mismatched signature, do not run it. Report the release version, download location, and signature details through the contact channel on [AvazTek's Larevixo page](https://avaztek.ir/software/larevixo). Do not send private keys, tokens, or other secrets in a report.

## License

Larevixo is distributed under the MIT License. Code signing establishes the publisher and integrity of a particular binary; it does not change the rights or conditions of that license.

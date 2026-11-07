# Code Signing Policy

This policy explains the signing status of Larevixo releases and how to verify Windows Authenticode signatures.

## Current status and SignPath application

Larevixo is preparing an application to the [SignPath Foundation free code-signing program](https://signpath.org/terms.html). The project has not been accepted, and no current Larevixo release or download has been signed with a SignPath Foundation certificate. Unless a particular release explicitly says otherwise and its signature verifies, treat its files as **unsigned**.

If accepted and signing is implemented, the certificate publisher for binaries signed through the free program will be SignPath Foundation, as described in the [SignPath Foundation terms](https://signpath.org/terms.html). The required attribution is: “Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).” This attribution describes the intended program and does not mean the application is approved or that any current file is signed.

In the future, AvazTek may separately obtain its own valid commercial code-signing certificate. Any binaries actually signed with that certificate may identify AvazTek as their verified publisher. This would be a separate signing arrangement and must not be confused with the free SignPath Foundation program.

## Signing responsibilities

The project is currently maintained by the GitHub account [avaztek-dev](https://github.com/avaztek-dev). At present, that account is the sole identified project author/committer, reviewer, and release approver; there is no separate reviewer or approval team. Changes from contributors who are not trusted committers require review by the project maintainer before release. If SignPath accepts the project, every signing request will receive the required manual approval from the release approver before signing.

See the [Privacy Policy](PRIVACY.md) for information about Larevixo's local data handling and network connections.

## Verify a Windows download

Use PowerShell to check the signature on an executable or installer:

```powershell
Get-AuthenticodeSignature .\Larevixo.exe | Format-List Status, StatusMessage, SignerCertificate
Get-ChildItem .\Larevixo-Setup-*.exe | ForEach-Object {
    Get-AuthenticodeSignature $_.FullName | Format-List Status, StatusMessage, SignerCertificate
}
```

For a file claimed to be signed, `Status` should be `Valid`. Check `SignerCertificate` against the publisher stated for that specific release: SignPath Foundation for a file signed through its free program, or AvazTek only for a file explicitly signed with AvazTek's own certificate. `NotSigned`, an invalid status, or a different signer means the file does not match that claim. Current files are unsigned unless their release record explicitly states otherwise and this check confirms it.

A valid Authenticode signature identifies the signer and helps verify file integrity. It does not guarantee that Windows SmartScreen warnings will be absent.

## Reporting a signing concern

If an official release has an unexpected, invalid, or mismatched signature, do not run it. Report the release version, download location, and signature details through the contact channel on [AvazTek's Larevixo page](https://avaztek.ir/software/larevixo). Do not send private keys, tokens, or other secrets in a report.

## License

Larevixo is distributed under the MIT License. Code signing establishes the publisher and integrity of a particular binary; it does not change the rights or conditions of that license.

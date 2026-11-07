# VISION data lifecycle

| Data                                    | Default / storage                                                    | Expiry and deletion                                                            |
| --------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Camera frames                           | Volatile bounded phone/PC memory; no recording                       | Replaced by latest frame, cleared on stop/disconnect                           |
| Pairing                                 | Android no-backup AES-GCM vault, key in Android Keystore             | Forget PC deletes phone key; operator revoke/restart invalidates server grants |
| Important events and capability changes | History off by default; encrypted JSON payload in app-private SQLite | At most seven days, or shorter chosen policy; 1,000 rows / 8 MiB cap           |
| Session summaries                       | Same opt-in store                                                    | User choice 1/7/30/90 days; shortening also expires existing rows              |
| Feedback and review state               | Embedded in encrypted local event                                    | Deleted with event; user rating is not independent ground truth                |
| Exported history                        | User-selected Android document destination only                      | User manages that external copy; export never enables collection               |
| Review drafts                           | Private Lab opt-in localStorage, packet hash bound                   | Seven-day validity; disabling draft storage deletes the saved draft            |
| Research objects                        | Explicit local content-addressed store                               | 10 MiB/object, 100 MiB/owner; withdrawal tombstones and retryable deletion     |
| Original private benchmark              | Separate immutable developer research asset                          | Not deleted by user-history/cache operations; never public deployment content  |

SQLite payloads use AES-GCM; random row IDs and retention timestamps are not
encrypted database pages. No-backup settings prevent restoring ciphertext without
the device key. Reinstallation normally removes app data and keys; real-device
reinstall acceptance remains pending. Exported files are outside that guarantee.

Cleanup runs on startup, record/read, and an Android scheduled daily job. Scheduling
is best effort: expiry is enforced on reads even when the OS delays jobs. Clear
Cache targets app cache only. Delete Event removes that row and compacts SQLite;
Delete All removes rows and rotates the history key. This does not promise forensic
erasure from flash hardware, independent exports, backups or remote replicas.
History Off stops new writes and feedback updates; existing entries remain available
for explicit export/deletion and normal expiry.

Dataset withdrawal is separate from local history deletion. `DatasetRegistry.withdraw`
persists a participant tombstone, invalidates affected versions, queues object deletion
and retries interrupted deletion after reopening. A withdrawn participant cannot be
implicitly re-enrolled. Consumers must resolve versions through the registry, not
trust an old exported manifest as current consent. Registry metadata itself contains
pseudonymous provenance; keep its directory access-controlled on encrypted disk.

Use `DatasetRegistry.export_reviewed` for a separately approved remote export.
It reserves bytes against a 100 MiB owner quota and records the destination and
object key before transfer. Retention ends at the earlier of consent expiry and
seven days. Withdrawal records a pending deletion even when the SDK is offline.
`reconcile_remote` registers expired objects and retries pending deletes for the
configured destination. The ledger retains the provider's delete acknowledgement.
Bucket lifecycle rules cover periods when the local operator is offline. Provider
versioning and backup expiry require separate verification. Tests use an injected
fixture client. The phone and public site use no remote storage configuration.

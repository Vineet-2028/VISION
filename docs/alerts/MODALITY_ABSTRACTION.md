# Modality abstraction

IMPLEMENTED: AlertRenderer.render(intent, now_ns) -> AlertPresentation. AlertPresenter.submit(intent, presentation, now_ns), channel_state(), reset(session_id). Local recording and null sinks share the contract. The recording sink retains bounded text only and performs no file I/O or speech on the perception thread. SessionRecorder owns optional disk recording.

No TTS added: actual hardware/speech is deferred to avoid platform-specific dependencies and blocking work. Browser speech synthesis may later be an optional non-authoritative demo. Android TextToSpeech is a future adapter, not a current application or dependency. Future asynchronous sinks must use a bounded latest slot, reject expired delivery, cancel superseded/reset output and expose actual busy state to Task016. Task016 owns preemption selection; Task017 must not rerank risk.

Haptic adapters may consume authorized direction, urgency and decision type directly from AlertIntent. UNKNOWN direction must not become a directional vibration. No haptics implemented. Future language packs implement AlertRenderer; future speech rate, verbosity, terminology and modality preferences need user research, not an account/profile framework now.

# Novelty and repeats

IMPLEMENTED: NEW, KNOWN, REAPPEARED, CHANGED, ESCALATED and DEESCALATED are explicit. Changed risk reason families are recorded as CHANGED but do not alone escalate; ordinal risk increases above the episode's highest announced level do. This high-water mark prevents HIGH/ELEVATED chatter from repeatedly escalating.

A newly eligible entity can announce immediately: no frame-count confirmation or initial debounce. Given Task014's 5.8% proxy recall, extra initial persistence would risk losing scarce evidence.

Novelty policy repeats only HIGH/SEVERE risk after both cooldown and repeat_interval, with continuous eligible evidence over that interval. ELEVATED does not generate periodic reminders. Gaps/unknown evidence restart the persistence requirement. Silence is not an all-clear message.

PROVISIONAL defaults: 5s same-entity cooldown, 30s persistence reminder, 5s reappearance gap, 60s retained suppression history. These are interruption research settings, not production-safe timing values.

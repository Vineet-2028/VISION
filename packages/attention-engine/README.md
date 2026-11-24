# Attention engine boundary

The current desktop research implementation is in apps/perception-lab/src/perception_lab/attention.py.
Its frozen attention_types.py contract is the Task017 boundary. This package remains
a future portable extraction point; no duplicate runtime or framework is introduced.
See docs/attention. No speech or validated safety behavior is implemented.

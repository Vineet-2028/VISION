# Sentinel public-dataset access request

Status: OPTIONAL_FUTURE_DATASET. Historical request PREPARED, NOT SENT; no account created or agreement executed.

Task006C uses user-owned footage. JRDB is not a completion dependency. Do not send this request.
Official pages checked 2026-10-15. The user selected arranging approved public
dataset access rather than supplying recorded footage.

## Preferred first source: JRDB pedestrian/campus subset

Official [registration](https://jrdb.erc.monash.edu/register/) requires first and
last name, institution/university, matching institutional email, supervisor,
password, and acceptance of the submission policy. Do not invent academic
affiliation or supervisor details. An independent developer should ask the dataset
team for the appropriate access route rather than filling false registration fields.

Verified publisher contact: **erc-jrdb@monash.edu**, listed on the
[official dataset page](https://jrdb.erc.monash.edu/dataset/).

Subject: JRDB access and permission for local Sentinel assistive-perception evaluation

Dear JRDB team,

I am developing Sentinel, a local-first assistive environment-perception research
prototype with a potential future proprietary product. I would like to request
the appropriate access route and written clarification of permitted use for a
small JRDB evaluation subset.

The proposed experiment would use approximately 10–20 short outdoor pedestrian,
campus and sidewalk sequences, sampling roughly 250–500 frames at deterministic
timestamps. We would evaluate existing pretrained object detectors locally against
the provided human bounding-box annotations, retain attribution, and publish only
aggregate evaluation results. We would not redistribute raw images, video or
annotations, upload the footage to third-party inference services, or train a model
in this experiment.

Could you please confirm whether this local evaluation in the context of a
potential commercial product is permitted under the applicable data terms, or
whether separate permission is required? Please also advise on registration for
an independent developer if institutional email and supervisor details do not apply.

For evaluation validity, we would appreciate guidance on recommended moving-camera
outdoor sequences, available occlusion metadata, and whether any release provides
exhaustive bicycle, motorcycle and vehicle annotations. If only people are annotated,
we will restrict JRDB scoring to people and will not treat other classes as negatives.

Thank you.

Sender details must be provided by the user before sending. Do not insert invented
identity, institutional affiliation or claims of ethics/permission approval.

## Complementary route: Ego4D

[Official access instructions](https://ego4d-data.org/docs/start-here/) require the
user to review and execute the agreement linked at ego4d.dev, then receive publisher
credentials. The publisher estimates approximately 48 hours. This is not instant
download permission. Never put access credentials in Git or a research report.

After approval, select a bounded outdoor walking subset and verify annotation
coverage before downloading. Ego4D's activity/object annotations must not be assumed
to provide exhaustive Sentinel P0 labels. Additional local annotation may be needed.

## Approval is an input, not a software check

No application has been submitted. Publisher approval and actual annotation coverage
cannot be manufactured by passing tests. Once permission and access are available,
use the [local evaluation workflow](../perception/REAL_WORLD_EVALUATION.md), preserve
source/license evidence and hashes, and keep calibration/test sequences separate.

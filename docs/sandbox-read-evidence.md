# Sandbox read-validation evidence

Live Sandbox results and report contents remain private and outside Git. Use only a
placeholder-shaped reference in C1 private evidence, C2 review/expiry, B9 pilot readiness, C3
approval planning, and the D5 Sandbox-to-Pilot flow.

Print the offline template:

```bash
make sandbox-read-evidence-template
```

The template records a private validation reference, run label, scope reference, RFI/Submittal
access statuses, pagination/filtering posture, reviewer placeholder, and expiry placeholder. It
contains no report contents, raw IDs, names, contacts, URLs, paths, payloads, credentials, or
attachment filenames.

Do not copy live stdout, API errors, screenshots, payloads, or generated report files into this
repository. A reference supports later private human review; it does not approve a pilot.

After private review, F3 can map this opaque ref alongside the smoke ref without reading source
contents. See [Sandbox evidence to Pilot](sandbox-evidence-to-pilot.md).

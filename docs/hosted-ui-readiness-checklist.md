# Hosted UI Readiness Checklist

Use this offline checklist before considering a private hosted evaluation:

- [ ] Every UI route and template has a known surface, page class, protection type, and mode status.
- [ ] Dashboard, admin, review, triage, and lifecycle surfaces retain admin protection.
- [ ] Lifecycle controls remain local-only and perform no Procore write-back.
- [ ] Attachment UI exposes metadata only and serves no file or object content.
- [ ] Export guidance remains command-only with no public download route.
- [ ] Demo-ready pages use only fake demo-marked data in local SQLite.
- [ ] Private, Sandbox, Pilot, and Hosted surfaces are hidden, disabled, or gated as appropriate.
- [ ] Templates contain no external scripts, styles, fonts, CDN assets, analytics, or telemetry.
- [ ] No frontend package manager, framework, or build system has been added.
- [ ] Private infrastructure and security review remains open before any hosted Pilot.

This checklist performs no deployment, live call, build, or external inspection. Passing it does
not approve production, Pilot, release, deployment, compliance, certification, or Procore use.

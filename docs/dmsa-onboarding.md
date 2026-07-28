# DMSA onboarding

The GC or Owner creates or installs a private Procore app for the integration. An app version
identifies the released configuration, while the **App Version Key** is the installation value
shared through a controlled channel. It is not a client secret and still must be handled carefully.

The installation uses a Developer Managed Service Account (DMSA): a dedicated, non-human identity
whose access does not depend on an employee account. The GC/Owner selects the projects the DMSA may
see and grants only the minimum read-only permissions.

For each customer connection:

1. Confirm the private app and approved version.
2. Confirm the DMSA identity and owning company.
3. Record only approved project IDs in `permitted_project_ids`.
4. Enable only RFIs and/or Submittals as contracted.
5. Grant Read Only access for those tools.
6. Verify attachments are visible through the permitted parent items.
7. Run the deterministic fixture health check in Phase A1.

Production onboarding must add a real secret manager. The database will retain only an opaque
`secret_name`/encrypted reference—not plaintext client IDs, client secrets, access tokens, or
refresh tokens. Live onboarding and token verification are not implemented in Phase A1.

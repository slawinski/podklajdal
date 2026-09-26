# 09 — Legal and Product Constraints

This document captures product constraints for delivery. It is not legal advice.

---

## 1. YouTube constraint

The application technically relies on yt-dlp to retrieve public YouTube media.

YouTube's Terms of Service restrict downloading/accessing content except where permitted by the service, rights holder, or applicable law. Therefore a technically successful implementation does not imply that every use of it is permitted.

MVP positioning should remain a local utility for content the user is entitled to process.

---

## 2. Copyright constraint

Separating vocals and instrumental does not remove copyright from the source work or recording.

The application must not imply that generated stems are automatically free to publish, redistribute, sell, or use commercially.

---

## 3. Product guardrails

MVP must not add functionality specifically intended to bypass:

- DRM;
- private-video access;
- authentication/paywalls;
- geographic/access controls;
- rights-management protections.

Cookies/authenticated YouTube sessions are explicitly out of scope.

---

## 4. User-facing notice

Recommended concise README notice:

```text
Use podkłajdal only with media you are entitled to download and process.
Downloading or reusing YouTube content may be restricted by YouTube's terms,
copyright, licences, or local law.
```

Do not show a blocking legal prompt on every CLI invocation.

---

## 5. Data/privacy posture

The local-first architecture intentionally minimizes privacy risk:

- audio processing is local;
- output is local;
- no podkłajdal account exists;
- no analytics/telemetry service exists;
- no source audio is uploaded to a podkłajdal server.

Network traffic still occurs to YouTube/related delivery infrastructure and model-hosting infrastructure used by dependencies.

---

## 6. Dependency licensing

Before distributing a packaged binary, delivery must review licences of:

- application dependencies;
- bundled FFmpeg build, if any;
- model files;
- PyTorch/ONNX Runtime components;
- transitive native libraries.

MVP may avoid bundling FFmpeg and require the user to install it separately, reducing redistribution/licensing complexity.

---

## 7. Naming / Tidal reference

`podkłajdal` is wordplay on Polish `podkład` + `Tidal`.

Before public/commercial distribution, perform a basic trademark/name review and avoid UI/branding that suggests affiliation with TIDAL.

MVP documentation should not claim integration with TIDAL.

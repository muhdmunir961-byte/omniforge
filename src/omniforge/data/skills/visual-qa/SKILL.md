---
name: visual-qa
description: "Audit live UI and real 3D product experiences for responsive visual regressions, functionality, accessibility, WebGL health, broken assets and measurable browser evidence."
---
# Visual QA — not just an attractive screenshot

## Trigger
After changes to layout, brand, interactivity, mobile navigation, 3D scenes or when user reports the page looks generic or interactions are broken.

## Audit phases
1. Identify baseline commit/URL, intended primary user journey and accepted visual reference. Separate aesthetic feedback from broken functionality.
2. Screenshot matrix: 1440x900, 1280x800, 768x1024, 390x844 and 360x800. Review overflow, typography hierarchy, image cropping, sticky headers, buttons and footers.
3. Follow every major CTA with actual click and destination. Test keyboard focus, forms, loading/error/empty/complete states and whether results are simulated or live.
4. Accessibility: headings and landmarks, contrast, keyboard-only path, aria labels and status, reduced motion, alt text, mobile tap targets.
5. 3D canvas: shader/link compile, actual vertices, model load, camera orbit, reset, fallback, WebGL context loss, no continuous GPU waste when hidden.
6. Browser errors: inspect console warnings, failed requests, network/asset dependency, dynamic state and edge inputs.
7. Performance: measure LCP, CLS, interaction latency and transferred scene/texture bundles where instrumentation allows. Don't invent measurements.
8. Record severity P0 security/core task, P1 functional/inaccessible/mobile, P2 legibility/performance, P3 optional polish.
9. Verify fixes in browser and attach screenshots, observed vs expected behavior, repro steps and linked test run.

## Executable offline quick-check
Run: python scripts/check_markup.py path/to/index.html

Bundled standard-library script checks **static HTML** for duplicate IDs, missing img alt, absent page lang/viewport, and externally hosted script references. It does not execute JavaScript or certify WCAG. For real interaction use Playwright/local Chromium with approval.

## Deliver
Prioritized findings, actual evidence, minimal fixes, and regression verification. Clearly mark untested third-party login and protected Vercel pages. No false claim that static analysis means full browser QA.
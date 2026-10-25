---
name: motion-interaction
description: "Design purposeful premium motion, animated UI and 3D camera transitions with CSS, Web Animations, Motion or GSAP while preserving accessibility and performance."
---
# Motion and Interaction

## Trigger
Use for microinteractions, gesture design, state transitions, page movement, scroll-driven narrative, Three.js camera motion and polished product UX.

## Choreography
1. Identify state changes: entering, opening, loading, submitting, completing, error, closing. Animation should communicate state or spatial relation.
2. Make a timing system: fast 120-180ms; UI 180-280ms; showcase 300-650ms. Use interruption-safe easing; avoid every element springing.
3. Prefer opacity/transform over layout-triggering properties. Never run unbounded requestAnimationFrame loops; clean up observers, events and timeline controllers.
4. For scroll transitions, prioritize natural scroll, keyboard navigation and immediate visible content. Avoid scroll-jacking and gating interaction behind animation.
5. For 3D, interpolate camera quaternion or position using real render loop, pause when not visible and provide orbit reset. No excessive spinning or simulated physics without reason.
6. On mobile, control animation density and pixel work; test touch actions. Ensure notifications do not cover primary actions or input keyboards.
7. Respect prefers-reduced-motion, implement no-motion state change equivalent, and maintain focus and screen reader context.
8. Check actual interactive output with Playwright where available and measure animation frame impact.

## CSS baseline
- Use transition: transform 160ms ease-out, opacity 160ms ease-out only on intended elements.
- Use focus-visible rings of adequate contrast.
- In media query prefers-reduced-motion: reduce, remove decorative motion while preserving visibility.
- Avoid skeleton loaders or fake progress without actual loading state.

## Deliver
A state transition map, animation tokens, implemented component code, browser evidence and any motion/performance regressions. Skill is instructional; optional libraries are NOT bundled, so inspect dependencies before proposing installs.
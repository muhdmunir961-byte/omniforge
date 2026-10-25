"use strict";
/* Run with node web-preview/tests/test_cli_batch.cjs */
const assert = require("node:assert/strict");
const { parse, splitConcatenated, MAX_COMMANDS } = require("../cli-batch.js");

const four = [
  "omniforge doctor",
  'omniforge search "API errors"',
  "ofprov snapshot",
  "ofprov tamper-demo",
];

assert.deepEqual(parse(four.join("\n")), four);
assert.deepEqual(parse(four.join(" ")), four);
assert.deepEqual(parse("  $ " + four.join("\n $ ") + " \n\n"), four);
assert.deepEqual(parse("omniforge search 'fix ofprov snapshot safely'"), [
  "omniforge search 'fix ofprov snapshot safely'",
]);
assert.deepEqual(parse('omniforge search "how omniforge doctor works" ofprov verify'), [
  'omniforge search "how omniforge doctor works"',
  "ofprov verify",
]);
assert.deepEqual(parse('omniforge search "API ; errors"'), [
  'omniforge search "API ; errors"',
]);
assert.deepEqual(parse("python --version omniforge doctor"), [
  "python --version",
  "omniforge doctor",
]);
assert.equal(splitConcatenated('omniforge search "ofprov snapshot"').length, 1);
for (const input of [
  "",
  " \n ",
  "omniforge doctor; rm -rf /",
  "omniforge doctor && python --version",
  "omniforge doctor | python --version",
  "omniforge doctor > /tmp/test",
  "omniforge doctor " + String.fromCharCode(96) + "whoami" + String.fromCharCode(96),
  "omniforge search 'unclosed",
  "omniforge doctor\n".repeat(MAX_COMMANDS + 1),
  "omniforge search " + "x".repeat(241),
  "omniforge doctor\n".repeat(110),
]) {
  assert.throws(() => parse(input), Error, "Unsafe or invalid input should fail: " + input.slice(0, 40));
}
console.log("PASS: safe batch parser, quote handling, collapsed mobile paste, six-command maximum and shell operator rejection");

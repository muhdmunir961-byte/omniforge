'use strict';
const path = require('node:path');
const { runTests } = require('@vscode/test-electron');

async function main() {
  await runTests({
    extensionDevelopmentPath: path.resolve(__dirname, '..'),
    extensionTestsPath: path.resolve(__dirname, 'host.js'),
    launchArgs: [
      '--no-sandbox',
      '--disable-gpu',
      '--disable-workspace-trust',
      '--skip-welcome',
      '--disable-telemetry'
    ]
  });
}
main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

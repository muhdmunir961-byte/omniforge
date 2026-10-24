'use strict';
const assert = require('node:assert/strict');
const vscode = require('vscode');

async function run() {
  // A contributed command activates its extension lazily. Execute first,
  // then inspect the registered commands to avoid a pre-activation false negative.
  await vscode.commands.executeCommand('omniforge.doctor');
  const expected = [
    'omniforge.doctor',
    'omniforge.search',
    'omniforge.load',
    'omniforge.install'
  ];
  const available = await vscode.commands.getCommands(true);
  for (const name of expected) {
    assert(available.includes(name), 'Command missing from VS Code host: ' + name);
  }
  // The command above invokes the installed CLI and opens its JSON result.
  const editor = vscode.window.activeTextEditor;
  assert(editor && editor.document, 'Diagnostics output not opened in an editor');
  assert.equal(editor.document.languageId, 'json');
  const output = JSON.parse(editor.document.getText());
  assert.equal(output.name, 'OmniForge');
  assert(output.skills.length >= 14);
  console.log('VS Code host integration passed: real command activation and CLI response');
}

module.exports = { run };

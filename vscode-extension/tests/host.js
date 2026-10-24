'use strict';
const assert = require('node:assert/strict');
const vscode = require('vscode');

async function run() {
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
  // This invokes OmniForge's installed CLI and opens its JSON result in the editor.
  await vscode.commands.executeCommand('omniforge.doctor');
  const editor = vscode.window.activeTextEditor;
  assert(editor && editor.document, 'Diagnostics output not opened in an editor');
  assert.equal(editor.document.languageId, 'json');
  const output = JSON.parse(editor.document.getText());
  assert.equal(output.name, 'OmniForge');
  assert(output.skills.length >= 14);
  console.log('VS Code host integration passed: real command activation and CLI response');
}

module.exports = { run };

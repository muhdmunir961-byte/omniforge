'use strict';
const vscode = require('vscode');
const { execFile } = require('node:child_process');

function projectRoot() {
  return vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length
    ? vscode.workspace.workspaceFolders[0].uri.fsPath : undefined;
}
function config() { return vscode.workspace.getConfiguration('omniforge'); }
function cli(args) {
  const exe = config().get('executable', 'omniforge');
  return new Promise((resolve, reject) => {
    execFile(exe, args, { cwd: projectRoot(), timeout: 30000, maxBuffer: 1024 * 512 }, (err, stdout, stderr) => {
      if (err) return reject(new Error(String(stderr || err.message).slice(0, 600)));
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('OmniForge returned invalid JSON')); }
    });
  });
}
async function showJson(title, data) {
  const doc = await vscode.workspace.openTextDocument({ content: JSON.stringify(data, null, 2), language: 'json' });
  await vscode.window.showTextDocument(doc, { preview: true });
}
async function chooseSkill(query) {
  const skills = await cli(['search', query, '--limit', '15']);
  if (!Array.isArray(skills) || !skills.length) {
    vscode.window.showInformationMessage('OmniForge: No matching skill found');
    return undefined;
  }
  const picked = await vscode.window.showQuickPick(skills.map(s => ({
    label: s.name, description: s.description, detail: `score ${s.score || 0}`
  })), { placeHolder: 'Select a skill' });
  return picked && picked.label;
}
function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand('omniforge.doctor', async () => {
    try { await showJson('OmniForge Doctor', await cli(['doctor'])); }
    catch (err) { vscode.window.showErrorMessage(String(err.message)); }
  }));
  context.subscriptions.push(vscode.commands.registerCommand('omniforge.search', async () => {
    const q = await vscode.window.showInputBox({ prompt: 'What capability do you need?', placeHolder: 'debug backend logs' });
    if (!q) return;
    try { await showJson('OmniForge Search', await cli(['search', q])); }
    catch (err) { vscode.window.showErrorMessage(String(err.message)); }
  }));
  context.subscriptions.push(vscode.commands.registerCommand('omniforge.load', async () => {
    const q = await vscode.window.showInputBox({ prompt: 'Search skills to read', placeHolder: 'sqlite schema' });
    if (!q) return;
    try {
      const name = await chooseSkill(q);
      if (!name) return;
      const result = await cli(['load', name]);
      const doc = await vscode.workspace.openTextDocument({ content: result.content, language: 'markdown' });
      await vscode.window.showTextDocument(doc, { preview: true });
    } catch (err) { vscode.window.showErrorMessage(String(err.message)); }
  }));
  context.subscriptions.push(vscode.commands.registerCommand('omniforge.install', async () => {
    const root = projectRoot();
    if (!root) { vscode.window.showWarningMessage('Open a project folder first'); return; }
    const q = await vscode.window.showInputBox({ prompt: 'Search skill to install', placeHolder: 'python symbols' });
    if (!q) return;
    try {
      const name = await chooseSkill(q);
      if (!name) return;
      const decision = await vscode.window.showWarningMessage(`Install '${name}' into ${root}?`, { modal: true }, 'Install');
      if (decision !== 'Install') return;
      const result = await cli(['install', name, '--agent', config().get('agent', 'codex'), '--project', root]);
      vscode.window.showInformationMessage(`OmniForge installed: ${result.installed}`);
    } catch (err) { vscode.window.showErrorMessage(String(err.message)); }
  }));
}
function deactivate() {}
module.exports = {activate, deactivate};

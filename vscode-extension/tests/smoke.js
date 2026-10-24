'use strict';
const assert = require('node:assert');
const Module = require('node:module');
const existing = Module._load;
const registered = [];
const fake = {
  commands: {registerCommand: (name, action) => {registered.push(name); return {dispose(){}};}},
  workspace: {workspaceFolders: [], getConfiguration: () => ({get:(_name, value) => value})},
  window: {}
};
Module._load = function(name, ...args) { if (name === 'vscode') return fake; return existing.apply(this, [name,...args]); };
try {
  const extension = require('../extension.js');
  const context = {subscriptions: []};
  extension.activate(context);
  assert.equal(registered.length, 4);
  assert.equal(context.subscriptions.length, 4);
  console.log('VS Code extension smoke passed (4 registered commands)');
} finally { Module._load = existing; }

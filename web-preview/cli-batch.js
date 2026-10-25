/* Public OmniForge CLI input parser.
 * Presentation only: server-side Python strictly allowlists every command.
 * It does not implement any shell operators or server execution.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.OmniForgeBatch = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const MAX_COMMANDS = 6;
  const MAX_SOURCE_LENGTH = 1500;
  const MAX_SINGLE_LENGTH = 240;
  const COMPLETE = [
    /^(?:omniforge|oforge) (?:doctor|list|inspect|--version)$/,
    /^(?:omniforge|oforge) (?:search|related|plan) .+$/,
    /^(?:omniforge|oforge) (?:load|catalog) .+$/,
    /^(?:omniforge|oforge) budget(?: --selected [a-z][a-z0-9-]*)?$/,
    /^ofprov (?:init|snapshot|verify|audit|proof|tamper-demo)$/,
    /^(?:omniforge|oforge) integrations (?:list|doctor)$/,
    /^python --version$/,
  ];
  function looksComplete(previous) {
    const value = previous.trim().replace(/\s+/g, " ");
    return COMPLETE.some(pattern => pattern.test(value));
  }
  function splitConcatenated(line) {
    const pieces = [];
    let start = 0, quote = "", escaped = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (escaped) { escaped = false; continue; }
      if (char === "\\") { escaped = true; continue; }
      if (quote) {
        if (char === quote) quote = "";
        continue;
      }
      if (char === "'" || char === '"') { quote = char; continue; }
      if (i <= start || !/\s/.test(line[i-1])) continue;
      if (!/^(?:omniforge|oforge|ofprov|python)(?=\s|$)/.test(line.slice(i))) continue;
      const before = line.slice(start, i).trim();
      if (!looksComplete(before)) continue;
      pieces.push(before);
      start = i;
    }
    pieces.push(line.slice(start).trim());
    return pieces.filter(Boolean);
  }
  function parse(source) {
    if (typeof source !== "string") throw Error("Input mesti teks biasa.");
    if (!source.trim()) throw Error("Masukkan sekurang-kurangnya satu command.");
    if (source.length > MAX_SOURCE_LENGTH) {
      throw Error("Terlalu panjang. Had maksimum ialah 1,500 aksara.");
    }
    if (source.includes("\0")) throw Error("Input mengandungi aksara kawalan yang tidak dibenarkan.");
    const commands = [];
    for (const rawLine of source.replace(/\r\n?/g, "\n").split("\n")) {
      const line = rawLine.trim().replace(/^\$\s+/, "");
      if (!line) continue;
      for (const part of splitConcatenated(line)) {
        if (part.length > MAX_SINGLE_LENGTH) {
          throw Error("Satu command terlalu panjang (maksimum 240 aksara). Pecahkan kepada baris berasingan.");
        }
        // Explicitly reject unquoted shell metacharacters.
        let quote = "", escape = false;
        for (const ch of part) {
          if (escape) { escape = false; continue; }
          if (ch === "\\") { escape = true; continue; }
          if (quote) { if (ch === quote) quote = ""; continue; }
          if (ch === "'" || ch === '"') { quote = ch; continue; }
          if (";&|<>".includes(ch) || ch.charCodeAt(0) === 96) {
            throw Error("Operator shell seperti ;, &&, | atau redirection tidak disokong. Gunakan satu command setiap baris.");
          }
        }
        if (quote) throw Error("Petikan command tidak lengkap. Tutup tanda petikan terlebih dahulu.");
        commands.push(part);
        if (commands.length > MAX_COMMANDS) {
          throw Error("Maksimum 6 command setiap Run. Pecahkan kepada batch kecil.");
        }
      }
    }
    if (!commands.length) throw Error("Masukkan sekurang-kurangnya satu command.");
    return commands;
  }
  return {parse, MAX_COMMANDS, MAX_SOURCE_LENGTH, MAX_SINGLE_LENGTH, splitConcatenated};
});

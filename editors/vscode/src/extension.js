"use strict";

const fs = require("fs");
const path = require("path");
const { workspace, window, commands, StatusBarAlignment } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

const WINDOWS = process.platform === "win32";

let client;
let status;
let output;
let resolved;

function exists(candidate) {
  try {
    return fs.statSync(candidate).isFile();
  } catch (error) {
    return false;
  }
}

function firstWorkspaceFolder() {
  const folders = workspace.workspaceFolders;
  return folders && folders.length ? folders[0].uri.fsPath : undefined;
}

function isCheckout(folder) {
  return exists(path.join(folder, "saerom", "lsp", "__init__.py"));
}

/** 폴더에서 위로 올라가며 새롬 저장소를 찾는다. */
function checkoutAbove(folder) {
  let here = folder;
  while (here) {
    if (isCheckout(here)) return here;
    const up = path.dirname(here);
    if (up === here) return undefined;
    here = up;
  }
  return undefined;
}

/** 작업 폴더와 열려 있는 문서에서 새롬 저장소를 찾는다. */
function findCheckout() {
  const starts = [];
  const folders = workspace.workspaceFolders || [];
  for (const folder of folders) starts.push(folder.uri.fsPath);
  for (const document of workspace.textDocuments) {
    if (document.uri.scheme === "file") starts.push(path.dirname(document.uri.fsPath));
  }
  for (const start of starts) {
    const found = checkoutAbove(start);
    if (found) return found;
  }
  return undefined;
}

/**
 * 언어 서버를 어떻게 띄울지 정한다. 앞에서부터 먼저 찾은 것을 쓴다.
 *
 *   1. saerom.serverPath 설정
 *   2. 작업 폴더의 .venv 안에 있는 saerom-lsp
 *   3. 작업 폴더의 .venv 안에 있는 파이썬
 *   4. saerom.pythonPath — 작업 폴더나 열린 문서 위쪽에 새롬 저장소가 있으면 거기서 실행한다
 */
function resolveServer() {
  const settings = workspace.getConfiguration("saerom");
  const explicit = (settings.get("serverPath") || "").trim();
  if (explicit) {
    return { command: explicit, args: [], reason: "saerom.serverPath 설정" };
  }

  const folder = firstWorkspaceFolder();
  if (folder) {
    const bin = path.join(folder, ".venv", WINDOWS ? "Scripts" : "bin");
    const script = path.join(bin, WINDOWS ? "saerom-lsp.exe" : "saerom-lsp");
    if (exists(script)) {
      return { command: script, args: [], reason: "작업 폴더의 .venv" };
    }
    const python = path.join(bin, WINDOWS ? "python.exe" : "python3");
    if (exists(python)) {
      return { command: python, args: ["-m", "saerom", "--lsp"], reason: "작업 폴더의 .venv" };
    }
  }

  const command = settings.get("pythonPath") || "python3";
  const options = {};
  let reason = "saerom.pythonPath 설정";
  const checkout = findCheckout();
  if (checkout) {
    options.cwd = checkout;
    options.env = Object.assign({}, process.env, { PYTHONPATH: checkout });
    reason = `새롬 저장소 ${checkout}`;
  }
  return { command, args: ["-m", "saerom", "--lsp"], options, reason };
}

function commandLine(server) {
  return [server.command].concat(server.args || []).join(" ");
}

function setStatus(state, tooltip) {
  if (!status) return;
  const marks = { starting: "$(sync~spin)", running: "$(check)", failed: "$(error)" };
  status.text = `${marks[state] || ""} 새롬`;
  status.tooltip = tooltip;
  status.command = "saerom.showStatus";
  status.show();
}

async function start() {
  resolved = resolveServer();
  const line = commandLine(resolved);
  output.appendLine(`언어 서버: ${line}  (${resolved.reason})`);
  if (resolved.options && resolved.options.cwd) {
    output.appendLine(`작업 디렉터리: ${resolved.options.cwd}`);
  }
  setStatus("starting", "새롬 언어 서버를 시작하는 중");

  const run = Object.assign({ transport: TransportKind.stdio }, resolved);
  client = new LanguageClient(
    "saerom",
    "새롬",
    { run, debug: run },
    {
      documentSelector: [{ scheme: "file", language: "saerom" }],
      synchronize: { fileEvents: workspace.createFileSystemWatcher("**/*.{sr,py}") },
      outputChannel: output,
    }
  );

  try {
    await client.start();
    setStatus("running", `새롬 언어 서버 실행 중\n${line}`);
    output.appendLine("언어 서버가 시작되었습니다.");
  } catch (error) {
    client = undefined;
    setStatus("failed", `새롬 언어 서버를 시작하지 못했습니다\n${line}`);
    output.appendLine(`시작 실패: ${error && error.message ? error.message : error}`);
    const choice = await window.showErrorMessage(
      `새롬 언어 서버를 시작하지 못했습니다: ${line}\n` +
        "새롬이 설치된 파이썬을 saerom.pythonPath 로 지정하거나, 새롬 저장소를 작업 폴더에 두십시오.",
      "자세히 보기"
    );
    if (choice) {
      output.show(true);
    }
  }
}

async function stop() {
  if (client) {
    await client.stop();
    client = undefined;
  }
}

function showStatus() {
  const line = resolved ? commandLine(resolved) : "(아직 정하지 않음)";
  const state = client ? "실행 중" : "멈춤";
  output.appendLine(`상태: ${state} — ${line}`);
  output.show(true);
  window.showInformationMessage(
    `새롬 언어 서버 ${state}: ${line}`,
    "다시 시작"
  ).then((choice) => {
    if (choice) commands.executeCommand("saerom.restartServer");
  });
}

async function activate(context) {
  output = window.createOutputChannel("새롬");
  status = window.createStatusBarItem(StatusBarAlignment.Right, 100);
  context.subscriptions.push(output, status);

  context.subscriptions.push(
    commands.registerCommand("saerom.restartServer", async () => {
      await stop();
      await start();
    }),
    commands.registerCommand("saerom.showStatus", showStatus)
  );

  await start();
}

function deactivate() {
  return stop();
}

module.exports = { activate, deactivate, resolveServer };

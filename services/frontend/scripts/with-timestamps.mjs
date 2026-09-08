import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const [command, ...args] = process.argv.slice(2);

if (!command) {
  throw new Error("A command is required");
}

const child = spawn(command, args, {
  env: process.env,
  stdio: ["inherit", "pipe", "pipe"],
});

function timestampLines(stream, output) {
  const lines = createInterface({ input: stream });
  lines.on("line", (line) => {
    output.write(`${new Date().toISOString()} ${line}\n`);
  });
}

timestampLines(child.stdout, process.stdout);
timestampLines(child.stderr, process.stderr);

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => child.kill(signal));
}

child.on("error", (error) => {
  process.stderr.write(`${new Date().toISOString()} ${error.message}\n`);
});

child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});

import pty from 'node-pty'
import { join } from 'path'
import os from 'os'

class TerminalManager {
  constructor() {
    this.terminals = new Map() // id -> { pty, type }
    this.nextId = 1
    this.logBuffer = [] // ring buffer for backend logs
    this.logMaxLines = 10000
    this.logSubscribers = new Set() // webContents that subscribed to logs
    this.mainWindow = null
  }

  setMainWindow(win) {
    this.mainWindow = win
  }

  // --- Backend Log Management ---

  appendLog(data) {
    this.logBuffer.push(data)
    if (this.logBuffer.length > this.logMaxLines) {
      this.logBuffer.splice(0, this.logBuffer.length - this.logMaxLines)
    }
    // Push to all subscribers
    this._broadcast('terminal-data', { id: 'backend-log', data })
  }

  getLogHistory() {
    return this.logBuffer.join('')
  }

  clearLog() {
    this.logBuffer = []
  }

  // --- PTY Terminal Management ---

  createTerminal(options = {}) {
    const id = `term-${this.nextId++}`
    const shell = options.shell || this._getDefaultShell()
    const cwd = options.cwd || os.homedir()
    const env = options.env || process.env
    const cols = options.cols || 80
    const rows = options.rows || 24

    const ptyProcess = pty.spawn(shell, [], {
      name: 'xterm-256color',
      cols,
      rows,
      cwd,
      env
    })

    ptyProcess.onData((data) => {
      this._broadcast('terminal-data', { id, data })
    })

    ptyProcess.onExit(({ exitCode, signal }) => {
      this._broadcast('terminal-exit', { id, exitCode, signal })
      this.terminals.delete(id)
    })

    this.terminals.set(id, { pty: ptyProcess, type: 'interactive' })
    return { id, pid: ptyProcess.pid }
  }

  writeToTerminal(id, data) {
    const term = this.terminals.get(id)
    if (term) {
      term.pty.write(data)
    }
  }

  resizeTerminal(id, cols, rows) {
    const term = this.terminals.get(id)
    if (term) {
      term.pty.resize(cols, rows)
    }
  }

  destroyTerminal(id) {
    const term = this.terminals.get(id)
    if (term) {
      term.pty.kill()
      this.terminals.delete(id)
    }
  }

  destroyAll() {
    for (const [id, term] of this.terminals) {
      try {
        term.pty.kill()
      } catch (e) {
        // ignore
      }
    }
    this.terminals.clear()
  }

  // --- Helpers ---

  _getDefaultShell() {
    if (process.platform === 'win32') {
      return 'powershell.exe'
    }
    return process.env.SHELL || '/bin/bash'
  }

  _broadcast(channel, payload) {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, payload)
    }
  }
}

export default new TerminalManager()

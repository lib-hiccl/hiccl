/**
 * WebShell terminal initialiser — creates an xterm.js instance wired to a
 * Hiccl binary stream for bidirectional PTY communication.
 *
 * Host element: <div class="hiccl-terminal" data-cid="..."></div>
 * Requires:     xterm.js, xterm-addon-fit, xterm-addon-weblinks, hiccl.js
 */
(function () {
  "use strict";

  var CTRL = 0xff;
  var STREAM_NAME = "terminal";

  function setStatus(cid, state) {
    var badge = document.getElementById("term-status-" + cid);
    if (!badge) return;
    badge.innerHTML = "";
    if (state === "live") {
      var dot = document.createElement("span");
      dot.className = "w-2 h-2 rounded-full bg-emerald-300 animate-pulse";
      badge.appendChild(dot);
      badge.appendChild(document.createTextNode(" live"));
      badge.className = "badge badge-success gap-1 font-mono text-xs py-3";
    } else if (state === "connecting") {
      var dot = document.createElement("span");
      dot.className = "w-2 h-2 rounded-full bg-amber-300 animate-pulse";
      badge.appendChild(dot);
      badge.appendChild(document.createTextNode(" connecting"));
      badge.className = "badge badge-warning gap-1 font-mono text-xs py-3";
    } else {
      badge.textContent = "closed";
      badge.className = "badge badge-ghost gap-1 font-mono text-xs py-3";
    }
  }

  function fail(cid, msg) {
    var host = document.getElementById("term-host-" + cid);
    if (!host) return;
    host.innerHTML =
      '<div style="color:#f87171;font-family:monospace;padding:1rem;white-space:pre-wrap">' +
      msg +
      "</div>";
    setStatus(cid, "closed");
  }

  function _initImpl(cid) {
    var host = document.getElementById("term-host-" + cid);
    if (!host) return;

    if (typeof Terminal === "undefined") {
      fail(
        cid,
        "xterm.js failed to load.\n" +
          "Expected /static/xterm.min.js — verify static_dir serves\n" +
          "examples/webshell/static/ and open the browser console for errors.",
      );
      return;
    }
    if (typeof hicclClient === "undefined") {
      fail(
        cid,
        "hiccl.js client not initialized (window.hicclClient missing).",
      );
      return;
    }

    var term = new Terminal({
      cursorBlink: true,
      fontFamily: "Menlo, Monaco, 'JetBrains Mono', 'Courier New', monospace",
      fontSize: 14,
      scrollback: 5000,
      theme: {
        background: "#0b0e14",
        foreground: "#e6e6e6",
        cursor: "#7dd3fc",
      },
    });

    var fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    if (typeof WebLinksAddon !== "undefined") {
      term.loadAddon(new WebLinksAddon.WebLinksAddon());
    }

    term.open(host);
    try {
      fitAddon.fit();
    } catch (e) {
      /* ignore */
    }

    var encoder = new TextEncoder();
    var currentStream = null;
    var disconnected = false;

    function wireStream() {
      disconnected = false;
      setStatus(cid, "connecting");
      term.write("\x1b[33mconnecting to shell...\x1b[0m\r\n");

      currentStream = hicclClient.createStream(STREAM_NAME, cid, {
        onData: function (data) {
          term.write(data);
        },
        onClose: function () {
          term.write("\r\n\x1b[31m*** terminal closed ***\x1b[0m\r\n");
          setStatus(cid, "closed");
          disconnected = true;
          term.write("\r\n\x1b[33mPress Enter to reconnect\x1b[0m\r\n");
        },
        onError: function (err) {
          term.write(
            "\r\n\x1b[31m*** stream error: " + String(err) + " ***\x1b[0m\r\n",
          );
          console.error("[webshell]", err);
          setStatus(cid, "closed");
          disconnected = true;
          term.write("\r\n\x1b[33mPress Enter to reconnect\x1b[0m\r\n");
        },
      });
    }

    term.onData(function (s) {
      if (disconnected) {
        if (s === "\r") {
          wireStream();
        }
        return;
      }
      if (currentStream) {
        currentStream.send(encoder.encode(s));
      }
    });

    term.onResize(function (size) {
      if (!currentStream || disconnected) return;
      var msg = encoder.encode(
        JSON.stringify({
          type: "resize",
          cols: size.cols,
          rows: size.rows,
        }),
      );
      var frame = new Uint8Array(msg.length + 1);
      frame[0] = CTRL;
      frame.set(msg, 1);
      currentStream.send(frame);
    });

    wireStream();
    term.focus();

    window.addEventListener("resize", function () {
      try {
        fitAddon.fit();
      } catch (e) {
        /* ignore */
      }
    });
  }

  function init(cid) {
    if (typeof hicclClient !== "undefined") {
      _initImpl(cid);
      return;
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        if (typeof hicclClient === "undefined") {
          fail(
            cid,
            "hiccl.js client not initialized (window.hicclClient missing).",
          );
          return;
        }
        _initImpl(cid);
      });
    } else {
      fail(
        cid,
        "hiccl.js client not initialized (window.hicclClient missing).",
      );
    }
  }

  window.WebShellTerminal = { init: init };
})();

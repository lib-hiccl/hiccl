/**
 * Hiccl Client — WebSocket / SSE real-time sync + htmx integration.
 *
 * Transport priority:
 *   1. WebSocket  (bidirectional — actions + push)
 *   2. SSE        (unidirectional push — actions fall back to HTTP)
 *   3. HTTP only  (htmx native AJAX, no real-time push)
 */
class HicclClient {
  constructor(sessionId, wsUrl, sseUrl) {
    this.sessionId = sessionId;
    this.wsUrl = wsUrl;
    this.sseUrl = sseUrl;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.ws = null;
    this.es = null;
    this.useWS = false;
    this.connect();
  }

  // ------------------------------------------------------------------
  // Connection lifecycle
  // ------------------------------------------------------------------

  connect() {
    this._tryWS();
  }

  _tryWS() {
    try {
      this.ws = new WebSocket(this.wsUrl);
    } catch (e) {
      console.warn("[hiccl] WebSocket creation failed, falling back to SSE");
      this._trySSE();
      return;
    }

    this.ws.onopen = () => {
      console.log("[hiccl] WebSocket connected");
      this.useWS = true;
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._handleMessage(msg);
      } catch (e) {
        console.error("[hiccl] WS parse error", e);
      }
    };

    this.ws.onclose = () => {
      this.useWS = false;
      console.log("[hiccl] WebSocket closed, reconnecting...");
      setTimeout(() => this._tryWS(), this.reconnectDelay);
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror
    };
  }

  _trySSE() {
    if (!this.sseUrl) {
      console.log("[hiccl] No SSE URL, using HTTP only");
      return;
    }

    try {
      this.es = new EventSource(this.sseUrl);
    } catch (e) {
      console.warn("[hiccl] SSE creation failed, using HTTP only");
      return;
    }

    this.es.addEventListener("hiccl", (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._handleMessage(msg);
      } catch (e) {
        console.error("[hiccl] SSE parse error", e);
      }
    });

    this.es.addEventListener("heartbeat", () => {
      // keepalive, no action needed
    });

    this.es.onopen = () => {
      console.log("[hiccl] SSE connected");
      this.reconnectDelay = 1000;
    };

    this.es.onerror = () => {
      console.log("[hiccl] SSE error, reconnecting...");
      // EventSource auto-reconnects, but we set a fallback
      setTimeout(() => {
        if (this.es.readyState === EventSource.CLOSED) {
          this._trySSE();
        }
      }, this.reconnectDelay);
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
    };
  }

  // ------------------------------------------------------------------
  // Message handling
  // ------------------------------------------------------------------

  _handleMessage(msg) {
    switch (msg.type) {
      case "batch":
        for (const patch of msg.patches) this._applyPatch(patch);
        break;
      case "patch":
        this._applyPatch(msg);
        break;
      case "error":
        console.error("[hiccl] Server error:", msg.message);
        break;
    }
  }

  _applyPatch(patch) {
    const target = document.getElementById(patch.component_id);
    if (!target) return;
    const html = patch.html;
    const swapStyle = patch.swap || "outerHTML";

    if (typeof htmx !== "undefined") {
      htmx.swap(target, html, { swapStyle });
    } else {
      if (swapStyle === "outerHTML") {
        target.outerHTML = html;
      } else {
        target.innerHTML = html;
      }
    }
  }

  // ------------------------------------------------------------------
  // Action sending (WS intercept)
  // ------------------------------------------------------------------

  sendAction(componentId, method, args = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "action",
          component_id: componentId,
          method,
          args,
        }),
      );
      return true;
    }
    return false; // Caller should fall back to HTTP
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.es) {
      this.es.close();
      this.es = null;
    }
  }
}

// ------------------------------------------------------------------
// htmx intercept: when WS is connected, route actions through WS
// ------------------------------------------------------------------

function interceptHtmxRequests(hicclClient) {
  if (typeof htmx === "undefined") return;

  document.addEventListener("htmx:configRequest", (event) => {
    if (!hicclClient.useWS) return;

    const path = event.detail.path;
    const match = path.match(/^\/hiccl\/action\/([^/]+)\/([^/]+)/);
    if (!match) return;

    const componentId = match[1];
    const method = match[2];

    // Collect parameters
    const args = {};
    if (event.detail.parameters) {
      for (const [k, v] of Object.entries(event.detail.parameters)) {
        args[k] = v;
      }
    }

    // Merge hx-vals
    const valsHeader = event.detail.headers?.["HX-vals"];
    if (valsHeader) {
      try {
        Object.assign(args, JSON.parse(valsHeader));
      } catch (e) {}
    }

    // Also try to get hx-vals from the triggering element
    const elt = event.detail.elt;
    if (elt) {
      const valsAttr = elt.getAttribute("hx-vals");
      if (valsAttr) {
        try {
          Object.assign(args, JSON.parse(valsAttr));
        } catch (e) {}
      }
    }

    // Send via WS and cancel the HTTP request
    if (hicclClient.sendAction(componentId, method, args)) {
      event.preventDefault(); // Cancel HTTP
    }
  });
}

// ------------------------------------------------------------------
// Initialization
// ------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  const meta = document.querySelector('meta[name="hiccl-session"]');
  if (!meta) return;

  const sessionId = meta.getAttribute("content");
  const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${location.host}/hiccl/ws/${sessionId}`;
  const sseUrl = `${location.origin}/hiccl/sse/${sessionId}`;

  window.hicclClient = new HicclClient(sessionId, wsUrl, sseUrl);
  interceptHtmxRequests(window.hicclClient);
});

// Bridge htmx page transitions (hx-boost) to Alpine.js tree re-initialization
document.addEventListener("htmx:afterSettle", (event) => {
  if (typeof Alpine !== "undefined") {
    if (typeof Alpine.discover === "function") {
      Alpine.discover();
    } else if (typeof Alpine.initTree === "function") {
      const target = (event.detail && event.detail.target) || event.target || document.body;
      Alpine.initTree(target);
    }
  }
});

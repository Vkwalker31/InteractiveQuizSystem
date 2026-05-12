export class SocketClient {
  constructor({ pin, clientId }) {
    this.pin = pin;
    this.clientId = clientId;
    this.ws = null;
    this.handlers = [];
    this.closeHandlers = [];
    this.messageQueue = []; 
  }

  connect() {
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const socketUrl = `${wsProtocol}${window.location.host}/ws/${this.pin}/${this.clientId}`;
    this.ws = new WebSocket(socketUrl);

    this.ws.onopen = () => {
      console.log("WebSocket connected!");
      while (this.messageQueue.length > 0) {
        const payload = this.messageQueue.shift();
        this.ws.send(JSON.stringify(payload));
      }
    };

    this.ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      this.handlers.forEach((h) => h(payload));
    };

    this.ws.onclose = () => {
      console.warn("WebSocket closed");
      this.closeHandlers.forEach((h) => h());
    };
  }

  onMessage(cb) { this.handlers.push(cb); }
  onClose(cb) { this.closeHandlers.push(cb); }

  send(payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    } else {
      this.messageQueue.push(payload);
    }
  }
}

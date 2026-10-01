/*
 * live.js — event-stream client with exponential backoff.
 *
 * Polls /api/matches/<id>/events?after=<seq> while the match is running, feeds new
 * events to a callback, and reports the terminal status. On network errors it backs
 * off and keeps retrying (never silently dies).
 */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const LIVE = new Set(["queued", "accepted", "ready", "running"]);

export class LiveClient {
  constructor(matchId, { onEvents, onStatus, onError }) {
    this.matchId = matchId;
    this.onEvents = onEvents || (() => {});
    this.onStatus = onStatus || (() => {});
    this.onError = onError || (() => {});
    this.lastSeq = 0;
    this.stopped = false;
    this.backoff = 700;
  }

  stop() {
    this.stopped = true;
  }

  async poll() {
    while (!this.stopped) {
      try {
        const res = await fetch(`/api/matches/${this.matchId}/events?after=${this.lastSeq}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const events = data.events || [];
        if (events.length) {
          events.forEach((e) => { this.lastSeq = e.sequence_number; });
          this.onEvents(events);
        }
        this.backoff = 700;
        if (LIVE.has(data.status)) {
          await sleep(this.backoff);
          continue;
        }
        this.onStatus(data.status);
        this.stopped = true;
        return;
      } catch (err) {
        this.onError(err);
        this.backoff = Math.min(5000, this.backoff * 2);
        await sleep(this.backoff);
      }
    }
  }
}

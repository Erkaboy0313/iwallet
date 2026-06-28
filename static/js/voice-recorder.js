/**
 * VoiceRecorder — small wrapper around the browser MediaRecorder API for
 * Epic 2 Story 2.1. The DOM glue (button click → start/stop, POST to
 * /app/voice/transcribe/) lives in _voice_button.html; this module stays
 * framework-agnostic so it can be unit-tested in principle.
 *
 * States: 'idle' | 'recording' | 'processing' | 'error'
 *
 * Usage:
 *   const r = new VoiceRecorder({
 *     onStateChange: (s) => { ... },
 *     maxDurationMs: 60000,
 *     silenceThresholdDb: -60,
 *     silenceTimeoutMs: 1500,
 *   });
 *   await r.start();
 *   const blob = await r.stop();   // returns the recorded Blob (audio/mp4 or audio/webm)
 *   r.cancel();                    // aborts without returning a blob
 */
(function (global) {
    "use strict";

    function UnsupportedError(message) {
        const e = new Error(message || "MediaRecorder not supported on this device");
        e.name = "UnsupportedError";
        return e;
    }

    function PermissionDeniedError(message) {
        const e = new Error(message || "Mikrofon ruxsati berilmadi");
        e.name = "PermissionDeniedError";
        return e;
    }

    // Pick the first MIME type the browser actually supports.
    // iOS Safari only does audio/mp4; Android Chrome + desktop prefer webm/opus.
    const PREFERRED_MIME_TYPES = [
        "audio/mp4",
        "audio/webm;codecs=opus",
        "audio/webm",
    ];

    function pickMimeType() {
        if (typeof global.MediaRecorder === "undefined") return null;
        for (const mt of PREFERRED_MIME_TYPES) {
            try {
                if (global.MediaRecorder.isTypeSupported(mt)) return mt;
            } catch (e) {
                /* some browsers throw if isTypeSupported is called with weird input */
            }
        }
        // Fall back to letting the browser pick its own default.
        return "";
    }

    function isSupported() {
        return (
            typeof global.MediaRecorder !== "undefined"
            && global.navigator
            && global.navigator.mediaDevices
            && typeof global.navigator.mediaDevices.getUserMedia === "function"
        );
    }

    class VoiceRecorder {
        constructor(opts) {
            opts = opts || {};
            this.onStateChange = opts.onStateChange || function () {};
            this.maxDurationMs = opts.maxDurationMs || 60000;          // 60s hard cap
            this.silenceThresholdDb = opts.silenceThresholdDb || -60;  // dBFS
            this.silenceTimeoutMs = opts.silenceTimeoutMs || 1500;     // 1.5s of silence -> auto stop
            this.silenceDetection = opts.silenceDetection !== false;   // default ON, can disable

            this._state = "idle";
            this._stream = null;
            this._recorder = null;
            this._chunks = [];
            this._mimeType = "";
            this._audioContext = null;
            this._analyser = null;
            this._silenceRafId = null;
            this._silenceStartTs = null;
            this._maxDurationTimer = null;
            this._stopResolve = null;
            this._stopReject = null;
        }

        get state() {
            return this._state;
        }

        get mimeType() {
            return this._mimeType;
        }

        _setState(next) {
            if (this._state === next) return;
            this._state = next;
            try {
                this.onStateChange(next);
            } catch (e) {
                /* swallow listener errors */
            }
        }

        async start() {
            if (this._state !== "idle") return;
            if (!isSupported()) {
                this._setState("error");
                throw UnsupportedError();
            }
            const mt = pickMimeType();
            if (mt === null) {
                this._setState("error");
                throw UnsupportedError();
            }
            this._mimeType = mt;

            try {
                this._stream = await global.navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (e) {
                this._setState("error");
                if (e && (e.name === "NotAllowedError" || e.name === "SecurityError")) {
                    throw PermissionDeniedError();
                }
                throw e;
            }

            try {
                const opts = mt ? { mimeType: mt } : undefined;
                this._recorder = new global.MediaRecorder(this._stream, opts);
            } catch (e) {
                this._releaseStream();
                this._setState("error");
                throw UnsupportedError();
            }
            this._chunks = [];

            this._recorder.addEventListener("dataavailable", (ev) => {
                if (ev.data && ev.data.size > 0) this._chunks.push(ev.data);
            });
            this._recorder.addEventListener("stop", () => {
                this._teardownLiveTimers();
                this._releaseStream();
                if (this._stopResolve) {
                    const blob = new Blob(this._chunks, { type: this._mimeType || "audio/webm" });
                    const r = this._stopResolve;
                    this._stopResolve = null;
                    this._stopReject = null;
                    r(blob);
                }
            });
            this._recorder.addEventListener("error", (ev) => {
                this._teardownLiveTimers();
                this._releaseStream();
                this._setState("error");
                if (this._stopReject) {
                    const rj = this._stopReject;
                    this._stopResolve = null;
                    this._stopReject = null;
                    rj(ev.error || new Error("MediaRecorder error"));
                }
            });

            this._recorder.start();
            this._setState("recording");
            this._armMaxDurationTimer();
            if (this.silenceDetection) this._armSilenceDetection();
        }

        /**
         * Stop recording and resolve with the recorded Blob. Transitions to
         * 'processing' since the caller almost always uploads next.
         */
        stop() {
            if (this._state !== "recording" || !this._recorder) {
                return Promise.resolve(null);
            }
            this._setState("processing");
            return new Promise((resolve, reject) => {
                this._stopResolve = resolve;
                this._stopReject = reject;
                try {
                    this._recorder.stop();
                } catch (e) {
                    this._stopResolve = null;
                    this._stopReject = null;
                    this._releaseStream();
                    this._setState("error");
                    reject(e);
                }
            });
        }

        /**
         * Cancel an in-flight recording — no blob is returned, state goes idle.
         */
        cancel() {
            if (this._recorder && this._state === "recording") {
                try { this._recorder.stop(); } catch (e) { /* noop */ }
            }
            this._teardownLiveTimers();
            this._releaseStream();
            this._stopResolve = null;
            this._stopReject = null;
            this._chunks = [];
            this._setState("idle");
        }

        reset() {
            this.cancel();
        }

        _armMaxDurationTimer() {
            this._maxDurationTimer = global.setTimeout(() => {
                if (this._state === "recording") {
                    // Caller can listen via onStateChange("processing") and toast separately.
                    this.stop().catch(() => {});
                }
            }, this.maxDurationMs);
        }

        _armSilenceDetection() {
            const AudioCtx = global.AudioContext || global.webkitAudioContext;
            if (!AudioCtx || !this._stream) return;
            try {
                this._audioContext = new AudioCtx();
                const src = this._audioContext.createMediaStreamSource(this._stream);
                this._analyser = this._audioContext.createAnalyser();
                this._analyser.fftSize = 1024;
                src.connect(this._analyser);
            } catch (e) {
                return;
            }
            const buf = new Uint8Array(this._analyser.fftSize);
            const linearThreshold = Math.pow(10, this.silenceThresholdDb / 20);
            this._silenceStartTs = null;

            const loop = () => {
                if (this._state !== "recording" || !this._analyser) return;
                this._analyser.getByteTimeDomainData(buf);
                // Compute RMS in [0, 1] from the time-domain buffer.
                let sumSq = 0;
                for (let i = 0; i < buf.length; i++) {
                    const v = (buf[i] - 128) / 128;
                    sumSq += v * v;
                }
                const rms = Math.sqrt(sumSq / buf.length);
                const now = global.performance ? global.performance.now() : Date.now();
                if (rms < linearThreshold) {
                    if (this._silenceStartTs === null) this._silenceStartTs = now;
                    else if (now - this._silenceStartTs > this.silenceTimeoutMs) {
                        this.stop().catch(() => {});
                        return;
                    }
                } else {
                    this._silenceStartTs = null;
                }
                this._silenceRafId = global.requestAnimationFrame(loop);
            };
            this._silenceRafId = global.requestAnimationFrame(loop);
        }

        _teardownLiveTimers() {
            if (this._maxDurationTimer) {
                global.clearTimeout(this._maxDurationTimer);
                this._maxDurationTimer = null;
            }
            if (this._silenceRafId && global.cancelAnimationFrame) {
                global.cancelAnimationFrame(this._silenceRafId);
                this._silenceRafId = null;
            }
            if (this._audioContext) {
                try { this._audioContext.close(); } catch (e) { /* noop */ }
                this._audioContext = null;
                this._analyser = null;
            }
            this._silenceStartTs = null;
        }

        _releaseStream() {
            if (this._stream) {
                try {
                    this._stream.getTracks().forEach((t) => t.stop());
                } catch (e) { /* noop */ }
                this._stream = null;
            }
        }
    }

    /**
     * Client-side silence/empty-blob detector. Story 2.5 AC: if user records
     * essentially nothing, don't even POST. Returns true when the blob looks
     * like silence (very small or near-zero peak amplitude).
     */
    async function isLikelySilent(blob) {
        if (!blob || blob.size < 1500) return true;
        const AudioCtx = global.AudioContext || global.webkitAudioContext;
        if (!AudioCtx) return false;
        let ctx;
        try {
            ctx = new AudioCtx();
            const arrayBuf = await blob.arrayBuffer();
            const audio = await ctx.decodeAudioData(arrayBuf.slice(0));
            if (audio.duration < 0.5) return true;
            const ch = audio.getChannelData(0);
            let peak = 0;
            for (let i = 0; i < ch.length; i++) {
                const v = Math.abs(ch[i]);
                if (v > peak) peak = v;
            }
            return peak < 0.01;
        } catch (e) {
            return false;
        } finally {
            if (ctx) { try { ctx.close(); } catch (e) { /* noop */ } }
        }
    }

    global.VoiceRecorder = VoiceRecorder;
    global.VoiceRecorderSupport = { isSupported, pickMimeType };
    global.VoiceRecorderErrors = { UnsupportedError, PermissionDeniedError };
    global.voiceIsLikelySilent = isLikelySilent;
})(typeof window !== "undefined" ? window : globalThis);

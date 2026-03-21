//odoo.define('metro_genie.metro_genie_voice', function (require) {
//    "use strict";
//
//    const FormController = require('web.FormController');
//
//    FormController.include({
//        renderButtons: function () {
//            this._super(...arguments);
//            console.log('OOOOOOOOO', this.modelName)
//            if (this.modelName === 'metro.genie.dashboard') {
//                const micBtn = document.getElementById('genie-mic');
//                console.log('micBtn', micBtn)
//                if (micBtn) {
//                    micBtn.addEventListener('click', () => {
//                        navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
//                            const recorder = new MediaRecorder(stream);
//                            const chunks = [];
//
//                            recorder.ondataavailable = e => chunks.push(e.data);
//                            recorder.onstop = () => {
//                                const blob = new Blob(chunks, { type: 'audio/webm' });
//                                const formData = new FormData();
//                                formData.append('audio', blob);
//
//                                // ✅ Get Flask API URL from context
//                                fetch('http://localhost:5000/process_audio', {
//                                    method: 'POST',
//                                    body: formData
//                                })
//                                .then(res => res.json())
//                                .then(data => {
//                                    const transcriptField = document.querySelector('textarea[name="transcript"]');
//                                    const parsedField = document.querySelector('textarea[name="parsed_json"]');
//
//                                    if (transcriptField) transcriptField.value = data.transcript;
//                                    if (parsedField) parsedField.value = data.parsed;
//                                });
//                            };
//
//                            recorder.start();
//                            setTimeout(() => recorder.stop(), 5000);
//                        }).catch(err => {
//                            console.error("Mic error:", err);
//                            alert("Microphone not accessible.");
//                        });
//                    });
//                }
//            }
//        }
//    });
//});


//odoo.define('metro_genie.metro_genie_voice', function (require) {
//    "use strict";
//
//    const FormController = require('web.FormController');
//    const rpc = require('web.rpc');
//
//    FormController.include({
//        renderButtons: function () {
//            this._super.apply(this, arguments);
//            console.log('thismodelName', this.modelName)
//            if (this.modelName === 'metro.genie.dashboard') {
//                setTimeout(() => {
//                    const micBtn = document.getElementById('genie-mic');
//
//                    if (micBtn) {
//                        console.log('thismodelName', this.modelName)
//                        micBtn.addEventListener('click', () => {
//                            console.log('Startttttttt')
//                            // Start recording
//                            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
//                                const mediaRecorder = new MediaRecorder(stream);
//                                const chunks = [];
//
//                                mediaRecorder.ondataavailable = event => {
//                                    chunks.push(event.data);
//                                };
//
//                                mediaRecorder.onstop = () => {
//                                    const blob = new Blob(chunks, { type: 'audio/wav' });
//                                    const formData = new FormData();
//                                    formData.append('audio', blob);
//
//                                    fetch('http://localhost:5000/process_audio', {
//                                        method: 'POST',
//                                        body: formData
//                                    })
//                                    .then(response => response.json())
//                                    .then(data => {
//                                        // Set values to fields
//                                        const $textarea = document.getElementById('genie-suggestion-input');
//                                        if ($textarea) {
//                                            $textarea.value = data.transcript || '';
//                                        }
//
//                                        // Optional: set parsed_json field using RPC
//                                        if (data && data.parsed_json) {
//                                            rpc.query({
//                                                model: 'metro.genie.dashboard',
//                                                method: 'write',
//                                                args: [[this.initialState.data.id], {
//                                                    parsed_json: JSON.stringify(data.parsed_json, null, 2),
//                                                }]
//                                            });
//                                        }
//                                    })
//                                    .catch(err => {
//                                        console.error("Flask fetch error:", err);
//                                        alert("Voice processing failed.");
//                                    });
//                                };
//
//                                mediaRecorder.start();
//
//                                // Record 5 seconds, then stop
//                                setTimeout(() => {
//                                    mediaRecorder.stop();
//                                    stream.getTracks().forEach(track => track.stop());
//                                }, 5000);
//                            });
//                        });
//                    }
//                }, 1000);
//            }
//        }
//    });
//});


odoo.define('metro_genie.genie_mic', function (require) {
    "use strict";

    var core = require('web.core');
    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    FormController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var self = this;

            this.$el.on('click', '#genie-mic', function () {
                alert("🎙️ Listening...");
                rpc.query({
                    model: 'metro.genie.dashboard',
                    method: 'genie_process_voice',
                    args: [],
                }).then(function (res) {
                    self.model.set(self.handle, {
                        transcript: res.transcript,
                        gpt_result: res.gpt_result,
                    });
                });
            });
        },
    });
});






const video = document.querySelector('video');

(async () => {
  try {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(v => v.kind === 'videoinput');
    const deviceId = devices.findIndex(v => v.label.includes("Back"))?.deviceId || devices[0].deviceId;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { width: 720, deviceId } });

    console.log(`stream: ${stream.id.substring(0, 4)}\nactive: ${stream.active}`);
    alert(`stream: ${stream.id.substring(0, 4)}\nactive: ${stream.active}`);
    
    video.srcObject = stream;
  } catch (err) {
    console.log(`err: ${err.name}: ${err.message}`);
    alert(`err: ${err.name}: ${err.message}`);
  }
})();

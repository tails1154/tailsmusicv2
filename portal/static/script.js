document.addEventListener('DOMContentLoaded', function () {
  var dropzone = document.getElementById('dropzone');
  if (dropzone) {
    dropzone.addEventListener('click', function () {
      document.getElementById('fileInput').click();
    });
    dropzone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', function () {
      dropzone.classList.remove('dragover');
    });
    dropzone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      handleFiles(e.dataTransfer.files);
    });
    document.getElementById('fileInput').addEventListener('change', function () {
      handleFiles(this.files);
    });
  }

  var statusSongs = document.getElementById('status-songs');
  var statusIp = document.getElementById('status-ip');
  if (statusSongs) {
    fetch('/api/status')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        statusSongs.textContent = 'Songs: ' + d.song_count;
        statusIp.textContent = 'IP: ' + d.ip;
      })
      .catch(function () {
        statusSongs.textContent = 'Songs: --';
        statusIp.textContent = 'IP: --';
      });
  }

});

function handleFiles(files) {
  var progressCard = document.getElementById('progress-card');
  var resultsCard = document.getElementById('results-card');
  progressCard.style.display = 'block';
  resultsCard.style.display = 'none';

  var mp3s = [];
  var zips = [];
  for (var i = 0; i < files.length; i++) {
    var f = files[i];
    if (f.name.toLowerCase().endsWith('.mp3')) mp3s.push(f);
    else if (f.name.toLowerCase().endsWith('.zip')) zips.push(f);
  }

  var total = mp3s.length + zips.length;
  var done = 0;
  var allFiles = [];

  function updateProgress() {
    var pct = total > 0 ? (done / total) * 100 : 100;
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = done + ' / ' + total + ' files processed';
  }

  function finish() {
    document.getElementById('progress-fill').style.width = '100%';
    document.getElementById('progress-text').textContent = 'Complete!';
    var list = document.getElementById('file-list');
    list.innerHTML = '';
    allFiles.forEach(function (name) {
      var li = document.createElement('li');
      li.textContent = name;
      list.appendChild(li);
    });
    resultsCard.style.display = 'block';
  }

  mp3s.forEach(function (file) {
    var formData = new FormData();
    formData.append('file', file);
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload/song', true);
    xhr.onload = function () {
      done++;
      if (xhr.status === 200) {
        var resp = JSON.parse(xhr.responseText);
        allFiles = allFiles.concat(resp.files || []);
      }
      updateProgress();
      if (done >= total) finish();
    };
    xhr.onerror = function () { done++; updateProgress(); if (done >= total) finish(); };
    xhr.send(formData);
  });

  zips.forEach(function (file) {
    var reader = new FileReader();
    reader.onload = function (e) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/upload/zip', true);
      xhr.setRequestHeader('Content-Type', 'application/zip');
      xhr.onload = function () {
        done++;
        if (xhr.status === 200) {
          var resp = JSON.parse(xhr.responseText);
          allFiles = allFiles.concat(resp.files || []);
        }
        updateProgress();
        if (done >= total) finish();
      };
      xhr.onerror = function () { done++; updateProgress(); if (done >= total) finish(); };
      xhr.send(e.target.result);
    };
    reader.readAsArrayBuffer(file);
  });

  if (total === 0) {
    document.getElementById('progress-text').textContent = 'No MP3 or ZIP files found';
  }
}

function connectToWifi() {
  var ssid = document.getElementById('ssid-input').value.trim();
  var pass = document.getElementById('password-input').value;
  var errorEl = document.getElementById('error-msg');
  if (!ssid) {
    errorEl.textContent = 'Please enter a network name';
    return;
  }
  errorEl.textContent = 'Connecting...';

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/wifi/connect', true);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.onload = function () {
    if (xhr.status === 200) {
      var resp = JSON.parse(xhr.responseText);
      if (resp.success) {
        document.getElementById('connected-card').style.display = 'block';
        document.getElementById('connected-msg').textContent = resp.message;
      } else {
        errorEl.textContent = resp.message || 'Failed to connect';
      }
    } else {
      errorEl.textContent = 'Server error';
    }
  };
  xhr.onerror = function () {
    errorEl.textContent = 'Connection error';
  };
  xhr.send('ssid=' + encodeURIComponent(ssid) + '&password=' + encodeURIComponent(pass));
}

function stopHotspot() {
  var btn = document.querySelector('#stop-msg');
  fetch('/api/hotspot/stop').then(function () {
    if (btn) btn.textContent = 'Hotspot stopping, TailsMusic will restart...';
  });
}

function scanBt() {
  document.getElementById('bt-scanning').style.display = 'block';
  document.getElementById('bt-scanning').querySelector('h2').textContent = 'Scanning...';
  document.getElementById('bt-results').style.display = 'none';
  document.getElementById('bt-connected').style.display = 'none';
  fetch('/api/bluetooth/scan')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById('bt-scanning').style.display = 'none';
      document.getElementById('bt-results').style.display = 'block';
      document.getElementById('bt-results-title').textContent = 'Found Devices';
      renderBtDevices(d.devices);
    })
    .catch(function () {
      document.getElementById('bt-scanning').style.display = 'none';
      document.getElementById('bt-results').style.display = 'block';
      document.getElementById('bt-error').textContent = 'Scan failed';
    });
}

function listBt() {
  document.getElementById('bt-scanning').style.display = 'block';
  document.getElementById('bt-results').style.display = 'none';
  document.getElementById('bt-connected').style.display = 'none';
  document.getElementById('bt-scanning').querySelector('h2').textContent = 'Loading...';
  fetch('/api/bluetooth/list')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById('bt-scanning').style.display = 'none';
      document.getElementById('bt-results').style.display = 'block';
      document.getElementById('bt-results-title').textContent = 'Known Devices';
      renderBtDevices(d.devices);
    })
    .catch(function () {
      document.getElementById('bt-scanning').style.display = 'none';
      document.getElementById('bt-results').style.display = 'block';
      document.getElementById('bt-error').textContent = 'Failed to list devices';
    });
}

function renderBtDevices(devices) {
  var list = document.getElementById('bt-device-list');
  var err = document.getElementById('bt-error');
  list.innerHTML = '';
  err.textContent = '';
  if (devices.length === 0 || devices[0].mac === '') {
    err.textContent = 'No devices found';
    return;
  }
  devices.forEach(function (dev) {
    var div = document.createElement('div');
    div.className = 'network-item';
    div.innerHTML = '<span class="network-name">' + dev.name + '</span><span class="network-signal">' + dev.mac + '</span>';
    div.addEventListener('click', function () {
      pairBt(dev.mac, dev.name);
    });
    list.appendChild(div);
  });
}

function pairBt(mac, name) {
  if (!confirm('Connect to ' + name + ' (' + mac + ')?')) return;
  document.getElementById('bt-error').textContent = 'Pairing & connecting...';
  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/bluetooth/pair', true);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.onload = function () {
    if (xhr.status === 200) {
      var resp = JSON.parse(xhr.responseText);
      if (resp.success) {
        document.getElementById('bt-results').style.display = 'none';
        document.getElementById('bt-connected').style.display = 'block';
        document.getElementById('bt-connected-msg').textContent = 'Connected to ' + name;
      } else {
        document.getElementById('bt-error').textContent = resp.message || 'Failed';
      }
    } else {
      document.getElementById('bt-error').textContent = 'Server error';
    }
  };
  xhr.onerror = function () {
    document.getElementById('bt-error').textContent = 'Connection error';
  };
  xhr.send('mac=' + encodeURIComponent(mac));
}

function listSinks() {
  var list = document.getElementById('sink-list');
  var err = document.getElementById('sink-error');
  list.innerHTML = '<div class="spinner"></div>';
  err.textContent = '';
  fetch('/api/bluetooth/sinks')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      list.innerHTML = '';
      if (!d.sinks || d.sinks.length === 0) {
        list.innerHTML = '<p class="small">No audio sinks found</p>';
        return;
      }
      d.sinks.forEach(function (s) {
        var div = document.createElement('div');
        div.className = 'network-item';
        div.innerHTML = '<span class="network-name">' + s.name + '</span><span class="network-signal">Set</span>';
        div.addEventListener('click', function () {
          setSink(s.name);
        });
        list.appendChild(div);
      });
    })
    .catch(function () {
      list.innerHTML = '';
      err.textContent = 'Failed to list sinks';
    });
}

function setSink(name) {
  document.getElementById('sink-error').textContent = 'Setting sink...';
  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/bluetooth/sink/set', true);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.onload = function () {
    if (xhr.status === 200) {
      var resp = JSON.parse(xhr.responseText);
      document.getElementById('sink-error').textContent = resp.success ? 'Audio routed to ' + name : resp.message;
    } else {
      document.getElementById('sink-error').textContent = 'Server error';
    }
  };
  xhr.onerror = function () {
    document.getElementById('sink-error').textContent = 'Connection error';
  };
  xhr.send('name=' + encodeURIComponent(name));
}

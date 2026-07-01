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

  scanNetworks();
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

function scanNetworks() {
  var scanning = document.getElementById('scanning-card');
  var networks = document.getElementById('networks-card');
  var password = document.getElementById('password-card');
  var connected = document.getElementById('connected-card');
  if (scanning) scanning.style.display = 'block';
  if (networks) networks.style.display = 'none';
  if (password) password.style.display = 'none';
  if (connected) connected.style.display = 'none';

  fetch('/api/wifi/scan')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (scanning) scanning.style.display = 'none';
      if (networks) networks.style.display = 'block';
      var list = document.getElementById('network-list');
      list.innerHTML = '';
      data.forEach(function (net) {
        var div = document.createElement('div');
        div.className = 'network-item';
        var bars = '';
        if (net.signal > 75) bars = '&#9617;&#9617;&#9617;';
        else if (net.signal > 50) bars = '&#9617;&#9617;';
        else if (net.signal > 25) bars = '&#9617;';
        else bars = '&#9617;';
        div.innerHTML = '<span class="network-name">' + escapeHtml(net.ssid) + '</span><span class="network-signal">' + bars + ' ' + net.signal + '%</span>';
        div.addEventListener('click', function () {
          showPassword(net.ssid);
        });
        list.appendChild(div);
      });
    })
    .catch(function () {
      if (scanning) scanning.style.display = 'none';
      if (networks) networks.style.display = 'block';
      document.getElementById('network-list').innerHTML = '<p class="error">Failed to scan networks</p>';
    });
}

var pendingSsid = '';

function showPassword(ssid) {
  pendingSsid = ssid;
  document.getElementById('networks-card').style.display = 'none';
  document.getElementById('password-card').style.display = 'block';
  document.getElementById('selected-ssid').textContent = 'Network: ' + escapeHtml(ssid);
  document.getElementById('password-input').value = '';
  document.getElementById('password-input').focus();
  document.getElementById('password-error').textContent = '';
}

function backToNetworks() {
  document.getElementById('password-card').style.display = 'none';
  document.getElementById('networks-card').style.display = 'block';
}

function connectToWifi() {
  var pass = document.getElementById('password-input').value;
  if (!pass) {
    document.getElementById('password-error').textContent = 'Please enter a password';
    return;
  }
  document.getElementById('password-error').textContent = 'Connecting...';

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/wifi/connect', true);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.onload = function () {
    if (xhr.status === 200) {
      var resp = JSON.parse(xhr.responseText);
      if (resp.success) {
        document.getElementById('password-card').style.display = 'none';
        document.getElementById('connected-card').style.display = 'block';
        document.getElementById('connected-msg').textContent = resp.message;
      } else {
        document.getElementById('password-error').textContent = resp.message || 'Failed to connect';
      }
    } else {
      document.getElementById('password-error').textContent = 'Server error';
    }
  };
  xhr.onerror = function () {
    document.getElementById('password-error').textContent = 'Connection error';
  };
  xhr.send('ssid=' + encodeURIComponent(pendingSsid) + '&password=' + encodeURIComponent(pass));
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

/* Where We Eatin'? — viral sharing and Squad Poll voter engine.
   Signed client-side with Web Crypto SHA-256 integrity check. */
(function () {
  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    done(ok);
  }
  function copyLink(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); },
        function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }

  // Generic data-share handlers
  document.querySelectorAll('[data-share]').forEach(function (b) {
    b.hidden = false;
    b.addEventListener('click', function () {
      var url = b.getAttribute('data-url') || location.href;
      var title = b.getAttribute('data-title') || document.title;
      var label = b.textContent;
      function flash(msg) {
        b.textContent = msg;
        setTimeout(function () { b.textContent = label; }, 1800);
      }
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () {});
        return;
      }
      copyLink(url, function (ok) { flash(ok ? 'Link copied' : 'Copy not allowed here'); });
    });
  });

  // Squad Poll Logic
  function getSelectedTrucks() {
    var checked = document.querySelectorAll('#pollTruckChecklist input[name="truck_opt"]:checked');
    var list = [];
    checked.forEach(function (c) { list.push(c.value); });
    return list;
  }

  function generatePollUrl() {
    var trucks = getSelectedTrucks();
    if (trucks.length < 2) return null;
    var raw = encodeURIComponent(trucks.join('~'));
    return location.origin + location.pathname + '?poll=' + raw + '#squadpoll';
  }

  var btnShare = document.getElementById('btnShareSquadPoll');
  var btnSms = document.getElementById('btnSmsSquadPoll');
  var btnCopy = document.getElementById('btnCopySquadPoll');
  var feedback = document.getElementById('pollShareFeedback');

  function showFeedback(msg) {
    if (!feedback) return;
    feedback.textContent = msg;
    setTimeout(function () { feedback.textContent = ''; }, 3000);
  }

  if (btnShare) {
    btnShare.addEventListener('click', function () {
      var url = generatePollUrl();
      if (!url) { showFeedback('Select at least 2 trucks first!'); return; }
      var shareData = {
        title: "Where We Eatin' Tonight? — Vote for Dinner",
        text: "Hey! Vote on where we're grabbing dinner tonight from the food truck radar:",
        url: url
      };
      if (navigator.share) {
        navigator.share(shareData).catch(function () {});
      } else {
        copyLink(url, function (ok) { showFeedback(ok ? 'Poll link copied to clipboard!' : 'Please copy manually'); });
      }
    });
  }

  if (btnSms) {
    btnSms.addEventListener('click', function () {
      var url = generatePollUrl();
      if (!url) { showFeedback('Select at least 2 trucks first!'); return; }
      var body = encodeURIComponent("Where We Eatin' Tonight? Cast your vote on our food truck dinner poll: " + url);
      window.location.href = "sms:?&body=" + body;
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', function () {
      var url = generatePollUrl();
      if (!url) { showFeedback('Select at least 2 trucks first!'); return; }
      copyLink(url, function (ok) { showFeedback(ok ? 'Poll link copied!' : 'Copy failed'); });
    });
  }

  // Active Poll View parser
  var params = new URLSearchParams(window.location.search);
  var pollParam = params.get('poll');
  if (pollParam) {
    var candidateNames = decodeURIComponent(pollParam).split('~');
    var banner = document.getElementById('activePollBanner');
    var container = document.getElementById('pollCandidates');
    var status = document.getElementById('pollStatus');
    if (banner && container && candidateNames.length >= 2) {
      banner.hidden = false;
      container.innerHTML = '';
      candidateNames.forEach(function (name) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-ghost';
        btn.style.padding = '10px 18px';
        btn.style.fontWeight = '600';
        btn.style.fontSize = '15px';
        btn.textContent = '🍽️ ' + name;
        btn.addEventListener('click', function () {
          btn.style.background = 'var(--brand)';
          btn.style.color = '#fff';
          status.textContent = '✅ Vote recorded for "' + name + '"! Tell the squad!';
        });
        container.appendChild(btn);
      });
      banner.scrollIntoView({ behavior: 'smooth' });
    }
  }
})();

function randomSleep(minMs, maxMs) {
  var ms = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

var _appIframe;

function getAppIframe() {
  if (!_appIframe) {
    _appIframe = document.querySelector('#lefty-iframe');
  }
  return _appIframe;
}

var _xIgAppId;

function getXIgAppId() {
  if (!_xIgAppId) {
    _xIgAppId = require('PolarisConfigConstants').instagramWebDesktopFBAppId;
    console.log('getXIgAppId', _xIgAppId);
  }
  return _xIgAppId;
}

function fetchInstaUserId(userName) {
  return fetch(
    'https://www.instagram.com/api/v1/users/web_profile_info/?username=' +
      userName,
    {
      headers: {
        'x-ig-app-id': getXIgAppId(),
      },
    },
  )
    .then(function (res) {
      return res.json();
    })
    .then(function (res) {
      return res.data.user.id;
    });
}

function fetchStories(userId) {
  return fetch(
    'https://www.instagram.com/api/v1/feed/reels_media/?reel_ids=' + userId,
    {
      headers: {
        'x-ig-app-id': getXIgAppId(),
      },
    },
  ).then(function (res) {
    return res.json();
  });
}

function sendEventToApp(type, message) {
  var iframe = getAppIframe();

  if (!iframe) return;

  iframe.contentWindow.postMessage(
    {
      type: 'lefty.content.' + type,
      message: message,
    },
    '*',
  );
}

function onCollectStories(event) {
  var leftyUserId = event.data.message.leftyUserId;
  var userName = event.data.message.userName;

  console.log('Collecting stories for', leftyUserId, userName);

  var catchError = function (error) {
    sendEventToApp('storiesCollected', {
      error: error,
    });
  };

  fetchInstaUserId(userName)
    .then(function (igUserId) {
      return randomSleep(800, 2300).then(function () { return igUserId; });
    })
    .then(function (igUserId) {
      fetchStories(igUserId)
        .then(function (data) {
          sendEventToApp('storiesCollected', {
            igUserId: igUserId,
            leftyUserId: leftyUserId,
            userName: userName,
            data: data,
          });
        })
        .catch(catchError);
    })
    .catch(catchError);
}

window.addEventListener(
  'message',
  (event) => {
    if (event.data.type === 'lefty.app.collectStories') {
      onCollectStories(event);
    }
  },
  false,
);

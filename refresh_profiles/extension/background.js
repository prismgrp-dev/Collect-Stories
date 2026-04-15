/**
 * Send message to content script
 */
function sendMessage(tabId, msg) {
  console.log('Send message:', msg.type);
  chrome.tabs.sendMessage(tabId, msg);
}

function isTabLoading(changeInfo) {
  return changeInfo.status === 'loading';
}

function isTabLoaded(changeInfo) {
  return changeInfo.status === 'complete';
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (isTabLoaded(changeInfo)) {
    // notify content script with the new tab url
    sendMessage(tabId, {
      type: 'lefty.background.tabs.onUpdated',
      url: tab.url,
    });
  }
});

// listen for click on the lefty icon in the browser top bar
chrome.action.onClicked.addListener((tab) => {
  sendMessage(tab.id, {
    type: 'lefty.background.toggleIframe',
  });
});

// listen form message coming from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background receive message', request);

  if (request.type === 'lefty.app.getLeftyCookie') {
    chrome.cookies.get(
      { url: 'https://app.lefty.io', name: 'leftyidv2' },
      (cookie) => {
        const val = cookie ? cookie.value : null;

        sendMessage(sender.tab.id, {
          type: 'lefty.background.cookie',
          cookie: val,
        });
      },
    );
  }

  if (request.type === 'lefty.app.setLeftyCookie') {
    chrome.cookies.set({
      url: 'https://app.lefty.io',
      domain: '.lefty.io',
      name: 'leftyidv2',
      value: request.cookie,
      secure: true,
      httpOnly: true,
      sameSite: 'lax',
    });
  }

  sendResponse();
  return true;
});

var params = new URLSearchParams(window.location.search)
var app = document.createElement('iframe');
app.style.height = '100%';
app.style.width = '100%';
app.style.border = 'none';
app.src = params.get('appUrl') + location.search;

document.body.append(app);

window.addEventListener('message', (e) => {
  app.contentWindow.postMessage(e.data, '*');
});
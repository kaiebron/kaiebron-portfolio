(function () {
  "use strict";

  var yr = document.getElementById("yr");
  if (yr) yr.textContent = new Date().getFullYear();

  var root = document.getElementById("weather");
  if (!root) return;

  var STALE_AFTER_MIN = 120; // Lambda runs every 30 min; flag if data is much older.

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function relTime(iso) {
    var mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    if (mins < 1) return "just now";
    if (mins < 60) return mins + " min ago";
    var h = Math.round(mins / 60);
    return h + (h === 1 ? " hour ago" : " hours ago");
  }

  function dayName(dateStr, i) {
    if (i === 0) return "Today";
    var d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString(undefined, { weekday: "short" });
  }

  function render(data) {
    root.textContent = "";
    var c = data.current;

    var now = el("div", "w-now");
    now.appendChild(el("div", "w-place", data.location));
    now.appendChild(el("div", "w-temp", Math.round(c.temp_f) + "°F"));
    now.appendChild(el("div", "w-sky", c.summary));
    var meta = el("div", "w-meta");
    [["Feels like", Math.round(c.feels_like_f) + "°"],
     ["Humidity", Math.round(c.humidity) + "%"],
     ["Wind", Math.round(c.wind_mph) + " mph"]].forEach(function (m) {
      var cell = el("div");
      cell.appendChild(el("span", null, m[0]));
      cell.appendChild(el("b", null, m[1]));
      meta.appendChild(cell);
    });
    now.appendChild(meta);
    root.appendChild(now);

    var days = el("div", "w-days");
    data.daily.forEach(function (d, i) {
      var card = el("div", "w-day");
      card.appendChild(el("div", "d", dayName(d.date, i)));
      card.appendChild(el("div", "s", d.summary));
      card.appendChild(el("div", "hi", Math.round(d.high_f) + "°"));
      card.appendChild(el("div", "lo", Math.round(d.low_f) + "°"));
      card.appendChild(el("div", "p", d.rain_chance + "% rain"));
      days.appendChild(card);
    });
    root.appendChild(days);

    var age = (Date.now() - new Date(data.updated_at).getTime()) / 60000;
    var foot = el("p", "w-foot" + (age > STALE_AFTER_MIN ? " stale" : ""),
      "Updated " + relTime(data.updated_at) + ". Source: " + data.source + "." +
      (age > STALE_AFTER_MIN ? " This is older than expected, so the scheduled job may be paused." : ""));
    root.appendChild(foot);
  }

  function fail(msg) {
    root.textContent = "";
    root.appendChild(el("p", "w-empty", msg));
  }

  fetch("data/weather.json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(render)
    .catch(function () {
      fail("The forecast isn't available right now. The backend publishes it every 30 minutes, so try again shortly.");
    });
})();

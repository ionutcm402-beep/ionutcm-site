/* ionutcm.com: gentle fade-in below the fold, and previous/next buttons for screenshot galleries.
   The site is complete without this file; it only adds polish. */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Fade in sections as they scroll into view. Anything already on screen is left alone.
  if (!reduce && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("revealed"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    var vh = window.innerHeight || 800;
    document.querySelectorAll(".reveal").forEach(function (el) {
      if (el.getBoundingClientRect().top > vh * 0.92) { el.classList.add("will-reveal"); io.observe(el); }
    });
  }

  // Gallery buttons: shown only where the strip actually overflows.
  document.querySelectorAll(".gallery").forEach(function (g) {
    var head = g.previousElementSibling;
    var nav = head && head.querySelector(".gallery-nav");
    if (!nav) return;
    var prev = nav.querySelector("[data-gallery-prev]");
    var next = nav.querySelector("[data-gallery-next]");
    function step() { var item = g.querySelector(".gallery-item"); return item ? item.getBoundingClientRect().width * 2 + 40 : 400; }
    function update() {
      var max = g.scrollWidth - g.clientWidth - 2;
      nav.hidden = max <= 0;
      prev.disabled = g.scrollLeft <= 2;
      next.disabled = g.scrollLeft >= max;
    }
    prev.addEventListener("click", function () { g.scrollBy({ left: -step(), behavior: reduce ? "auto" : "smooth" }); });
    next.addEventListener("click", function () { g.scrollBy({ left: step(), behavior: reduce ? "auto" : "smooth" }); });
    g.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  });
})();

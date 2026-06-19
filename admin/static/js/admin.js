// Admin panel client helpers.
(function () {
  // Confirm before destructive POST form submits (block / unblock).
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.getAttribute('data-confirm'))) {
        e.preventDefault();
      }
    });
  });

  // Auto-refresh the dashboard every 30s so live stats stay current.
  if (document.body.dataset.autorefresh === '1') {
    setTimeout(function () { window.location.reload(); }, 30000);
  }

  // Sidebar hide/show toggle — persist the collapsed state across pages.
  var toggle = document.getElementById('sidebarToggle');
  if (localStorage.getItem('sidebarCollapsed') === '1') {
    document.body.classList.add('sidebar-collapsed');
  }
  if (toggle) {
    toggle.addEventListener('click', function () {
      var collapsed = document.body.classList.toggle('sidebar-collapsed');
      localStorage.setItem('sidebarCollapsed', collapsed ? '1' : '0');
    });
  }

  // Profile dropdown (top-right) — toggle on click, close on outside click.
  var profileMenu = document.getElementById('profileMenu');
  var profileBtn = document.getElementById('profileBtn');
  if (profileMenu && profileBtn) {
    profileBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      profileMenu.classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (!profileMenu.contains(e.target)) {
        profileMenu.classList.remove('open');
      }
    });
  }
})();

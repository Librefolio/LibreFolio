document.addEventListener("DOMContentLoaded", function () {
    // Use relative paths for deployment flexibility
    const healthUrl = "/api/v1/system/health";
    const dashboardUrl = "/";
    const fallbackUrl = "getting-started/installation/"; // Relative to index.md

    // 1. Check Homepage Button
    const dashboardBtn = document.getElementById("dashboard-link");

    // 2. Check Navigation Links (Sidebar and Top Tabs)
    // We look for any link pointing to the dashboard URL
    const allLinks = document.querySelectorAll('a[href="' + dashboardUrl + '"], a[href="/"]');
    const navItemsToHide = [];

    allLinks.forEach(link => {
        // Identify if this is a navigation link (sidebar or tabs)
        // Material MkDocs uses .md-nav__link for sidebar and .md-tabs__link for top tabs
        if (link.classList.contains('md-nav__link') || link.classList.contains('md-tabs__link')) {
            // Find the parent list item (li) to hide
            const parentItem = link.closest('li');
            if (parentItem) {
                navItemsToHide.push(parentItem);
            }
        }
    });

    // Function to update UI based on status
    function updateUI(isOnline) {
        console.log("Dashboard status:", isOnline ? "ONLINE" : "OFFLINE");

        // Update Homepage Button
        if (dashboardBtn) {
            if (isOnline) {
                dashboardBtn.href = dashboardUrl;
                dashboardBtn.classList.remove("md-button--disabled", "md-button--secondary");
                dashboardBtn.innerHTML = "Go to Dashboard 🚀";
                dashboardBtn.title = "Go to Dashboard";
            } else {
                dashboardBtn.href = fallbackUrl;
                dashboardBtn.innerHTML = "Server Offline - Setup Guide 📘";
                dashboardBtn.classList.add("md-button--secondary");
            }
        }

        // Update Nav Links
        navItemsToHide.forEach(item => {
            if (isOnline) {
                item.style.display = ""; // Restore default display
            } else {
                item.style.display = "none"; // Hide
            }
        });
    }

    // Offline-first: Start with offline state, then check server
    updateUI(false);

    // Perform health check
    fetch(healthUrl)
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error("Server not OK");
        })
        .then(data => {
            if (data.status === "ok") {
                updateUI(true);
            } else {
                throw new Error("Invalid status");
            }
        })
        .catch(error => {
            // Server not reachable - keep offline state
            console.log("Dashboard server not reachable:", error.message);
        });
});

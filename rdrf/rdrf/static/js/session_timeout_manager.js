function ModalSessionNotifier(options) {

    const settings = $.extend({
        $modal: undefined,
        sessionExpiryTimeoutSelector: undefined
    }, options);

    const SessionState = {
        Expiring: "expiring",
        Expired: "expired"
    }

    const $sessionTimeoutModal = settings.$modal;
    const $sessionExpiredComponents = $(`[data-session-state="${SessionState.Expired}"]`);
    const $sessionExpiringComponents = $(`[data-session-state="${SessionState.Expiring}"]`);
    const sessionTimeoutModal = new bootstrap.Modal($sessionTimeoutModal, {backdrop: "static"});
    let countdownInterval;

    function updateSessionTimeoutMessage(secondsLeft) {
        const ONE_MINUTE_IN_SECONDS = 60;
        let timeoutText = "";

        if (secondsLeft >= ONE_MINUTE_IN_SECONDS) {
            const minutesLeft = Math.round(secondsLeft / ONE_MINUTE_IN_SECONDS);
            timeoutText = interpolate(ngettext("%s minute", "%s minutes", minutesLeft), [minutesLeft]);
        } else {
            timeoutText = interpolate(ngettext("%s second", "%s seconds", secondsLeft), [secondsLeft]);
        }

        $sessionTimeoutModal.find(settings.sessionExpiryTimeoutSelector).text(timeoutText);
    }

    function displayComponents(sessionState) {
        switch (sessionState) {
            case SessionState.Expiring: {
                $sessionExpiredComponents.addClass("d-none");
                $sessionExpiringComponents.removeClass("d-none");
                break;
            }
            case SessionState.Expired: {
                $sessionExpiredComponents.removeClass("d-none");
                $sessionExpiringComponents.addClass("d-none");
                $('.modal-backdrop').css("opacity", ".9");
                break;
            }
        }
    }

    function clearCountdownTimer() {
        if (countdownInterval) clearInterval(countdownInterval);
    }

    function show(secondsLeftInSession) {
        let secondsUntilNextCountdownUpdate = 30;

        function countdownTimer() {
            if (secondsLeftInSession > 0) {
                updateSessionTimeoutMessage(secondsLeftInSession);
                if (secondsLeftInSession === 30) {
                    clearCountdownTimer();
                    secondsUntilNextCountdownUpdate = 10;
                    countdownInterval = setInterval(countdownTimer, secondsUntilNextCountdownUpdate * 1000);
                }
                secondsLeftInSession -= secondsUntilNextCountdownUpdate;
            } else {
                clearCountdownTimer();
                displayComponents(SessionState.Expired)
            }
        }

        countdownInterval = setInterval(countdownTimer, secondsUntilNextCountdownUpdate * 1000);
        countdownTimer();
        displayComponents(SessionState.Expiring);
        sessionTimeoutModal.show();
    }

    return {
        clearCountdownTimer,
        show
    }
}

function SessionManager(sessionNotifier, options) {

    const settings = $.extend({
      session: {
          maxAge: undefined,
          warningLeadTime: undefined,
          refreshLeadTime: undefined
      },
      urls: {
          sessionRefresh: undefined,
          login: undefined,
          logout: undefined
      }
    }, options);

    const maxSessionAge = settings.session.maxAge;
    const sessionWarningLeadTime = settings.session.warningLeadTime;
    const sessionRefreshLeadTime = settings.session.refreshLeadTime;
    const secondsUntilNextSessionRefresh = maxSessionAge - sessionRefreshLeadTime;
    const secondsUntilExpiryWarning = maxSessionAge - sessionWarningLeadTime;
    let sessionRefreshInterval;
    let restartCount = 0;

    function keepAlive(forcedRefresh = false) {
        const data = {};
        if (forcedRefresh) data['forced_refresh'] = true;
        return $.ajax({
            url: settings.urls.sessionRefresh,
            type: "get",
            data
        })
            .fail(function() { alert(gettext("Error while refreshing session. Please check your connection"));
        });
    }

    function restart() {
        sessionNotifier.clearCountdownTimer();

        const sessionRefresh = (forcedRefresh = false) => {
            keepAlive(forcedRefresh).then(function ( data, status, jqXHR ) {
                if (data && !data.success) {
                    clearInterval(sessionRefreshInterval);
                    setTimeout(() => { sessionNotifier.show(sessionWarningLeadTime) }, secondsUntilExpiryWarning * 1000);
                }
            });
        }

        if (restartCount > 0) {
            sessionRefresh(true);
        }
        restartCount += 1;

        sessionRefreshInterval = setInterval(sessionRefresh, secondsUntilNextSessionRefresh * 1000);
    }

    function logout() {
        window.location.href = settings.urls.logout;
    }

    function goToLoginPage() {
        window.location.href = settings.urls.login;
    }

    // initialise session manager
    restart();

    return {
        restart,
        logout,
        goToLoginPage
    }

}
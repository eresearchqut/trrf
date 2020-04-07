/*
 * jquery.userTimeout.js
 * @version: v0.5.1
 * @author: Luke LeBlanc
 *
 * Copyright (c) 2017 Luke LeBlanc
 *
 * GNU General Public License v3 (http://www.gnu.org/licenses/)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 */

;(function ($, document, window, undefined) {
	'use strict';

	$.fn.userTimeout = function (opts) {
		var $defaults = {
			logouturl: null,                   		// ULR to redirect to, to log user out
			referer: false,                    		// URL Referer - false, auto or a passed URL
			refererName: 'refer',              		// Name of the passed referal in the URL
			notify: true,                      		// Toggle for notification of session ending
			timer: true,                       		// Toggle for enabling the countdown timer
			session: 600000,                   		// 10 Minutes in Milliseconds, then notification of logout
			force: 10000,                      		// 10 Seconds in Milliseconds, then logout
			ui: 'auto',                        		// Model Dialog selector (auto, bootstrap, jqueryui)
			debug: false,                      		// Shows alerts
			modalTitle: 'Session Timeout',     		// Modal Title
			modalBody: 'You\'re being timed out due to inactivity. Please choose to stay signed in or to logoff. Otherwise, you will logged off automatically.',  // Modal body content
			modalLogOffBtn: 'Log Off',		   		// Modal log off button text
			modalStayLoggedBtn: 'Stay Logged In'	// Modal stay logged in button text
		};

		var $options = $.extend($defaults, opts || {});

		var $timeoutTimer, $logoutTimer, $countDownTimer, $startTime, $elapsedTime, $elapsedCounterTime, $timeDiff, $modalUI;

		/**
		 * var init -
		 *
		 * Initializes the plugin. It first does some basic error checking
		 * to ensure the plugin is properly configured, then checks to ensure
		 * one of the two dependencies is available within the page in order
		 * to utilize the modal feature of the plugin. It finishes by starting
		 * the session timeout.
		 *
		 * @return {undefined}
		 */
		var init = function() {
			if (!$options.logouturl) {
				if ($options.debug === true) {
					window.alert('Please configure the userTimeout plugin!');
				} else {
					window.console.error('Please configure the userTimeout plugin!');
				}

				return;
			}

			if (uiCheck($options.ui) === false) {
				return;
			}

			startTimer();

			$(document).on('focus click mousemove mousedown keyup scroll keypress', function () {
				startTimer();
			});
		};

		/**
		 * var startTimer -
		 *
		 * Initially clears all timers to ensure a clean slate, sets the start
		 * time and then based on the type of timer being used, it will start
		 * the timeout process.
		 *
		 * @param  {string or null} type [Used to distinguish what type of timer
		 * is being used]
		 * @return {undefined}
		 */
		var startTimer = function (type) {
			clearTimeout($timeoutTimer);
			clearTimeout($logoutTimer);

			$startTime = new Date().getTime();
			$elapsedTime = 0;
			$elapsedCounterTime = 0;

			switch (type) {
				case 'logout':
					$countDownTimer = Math.floor($options.force / 1000);
					$logoutTimer = setTimeout(function () { checkTimer(type); }, 100);
					break;
				default:
					$timeoutTimer = setTimeout(function () { checkTimer(type); }, 100);
					break;
			}
		};

		/**
		 * var checkTimer -
		 *
		 * Main processor of the timeout script. Every 0.1 seconds, this function
		 * records the elapsed time it's been executing and calculates the difference
		 * from the current time with the start time. Based on which type of timer is
		 * being initiated, it will either continue on to the next phase of execution
		 * or continue to run until the elapsed time matches the time set in the config.
		 *
		 * @param  {string or null} type [Used to distinguish what type of timer
		 * is being used]
		 * @return {undefined}
		 */
		var checkTimer = function (type) {
			$elapsedTime += 100;
			$timeDiff = (new Date().getTime() - $startTime) - $elapsedTime;

			switch (type) {
				case 'logout':
					if ($elapsedTime === $options.force) {
						logout();
					} else {
						$elapsedCounterTime += 100;

						if ($elapsedCounterTime === 1000 && $countDownTimer !== 0) {
							$countDownTimer -= 1;
							$('#countdowntimer').html($countDownTimer);
							$elapsedCounterTime = 0;
						}

						$logoutTimer = setTimeout(function () { checkTimer(type); }, (100 - $timeDiff));
					}

					break;
				default:
					if ($elapsedTime === $options.session) {
						if ($options.notify === true) {
							modal();
						} else {
							logout();
						}
					} else {
						$timeoutTimer = setTimeout(function () { checkTimer(type); }, (100 - $timeDiff));
					}

					break;
			}
		};

		/**
		 * var uiCheck -
		 *
		 * Checks to see if either bootstrap or jQuery UI is available within the page.
		 * Otherwise, false will be given. Based on what this function returns, will
		 * determine which modal, if any at all, will be used.
		 *
		 * @param  {string or boolean (false)} uiTest [String or boolean (false) given
		 * from the passed options of the plugin]
		 * @return {boolean (true or false)} [Returns false if unable to determine if
		 * bootstrap or jQuery UI is available within the page, otherwise returns true]
		 */
		var uiCheck = function (uiTest) {
			switch (uiTest) {
				case 'auto':
					if (typeof $().emulateTransitionEnd === 'function') {
						$modalUI = 'bootstrap';
					} else if (typeof jQuery.ui !== 'undefined') {
						$modalUI = 'jqueryui';
					} else {
						if ($options.debug === true) {
							window.alert('Twitter Bootstrap 3 nor jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
						} else {
							window.console.error('Twitter Bootstrap 3 nor jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
						}

						return false;
					}

					break;
				case 'bootstrap':
					if (typeof $().emulateTransitionEnd !== 'function') {
						if ($options.debug === true) {
							window.alert('Twitter Bootstrap 3 was not found! Please load the proper libraries and their themes to utilize this plugin!');
						} else {
							window.console.error('Twitter Bootstrap 3 was not found! Please load the proper libraries and their themes to utilize this plugin!');
						}

						return false;
					} else {
						$modalUI = 'bootstrap';
					}

					break;
				case 'jqueryui':
					if (typeof jQuery.ui === 'undefined') {
						if ($options.debug === true) {
							window.alert('jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
						} else {
							window.console.error('jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
						}

						return false;
					} else {
						$modalUI = 'jqueryui';
					}

					break;
				default:
					if ($options.debug === true) {
						window.alert('Twitter Bootstrap 3 nor jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
					} else {
						window.console.error('Twitter Bootstrap 3 nor jQueryUI was not found! Please load the proper libraries and their themes to utilize this plugin!');
					}

					return false;
			}

			return true;
		};

		/**
		 * var modal -
		 *
		 * Creates and displays the modal to the end user based on the configuration
		 * of the plugin. If the modal is bootstrap and the settings for the timer
		 * are set to true, the countdown timer will display.
		 *
		 * @return {undefined}
		 */
		var modal = function () {
			startTimer('logout');

			$(document).on('focus click mousemove mousedown keyup scroll keypress', function () {
				startTimer('logout');
			});

			if ($modalUI === 'bootstrap') {
				var $container, $dialog, $content, $header, $body, $footer, $logoutBtn;

				$container = $('<div class="modal fade" id="notifyLogout" tabindex="-1" role="dialog" aria-labelledby="notifyLogoutLabel" aria-hidden="true"></div>');
				$dialog = $('<div class="modal-dialog"></div>');
				$content = $('<div class="modal-content"></div>');
				$header = $('<div class="modal-header"><button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button><h4 class="modal-title" id="notifyLogoutLabel">' + $options.modalTitle + '</h4></div>');
				$body = $('<div class="modal-body">' + $options.modalBody + '</div>');

				if ($options.timer === true) {
					$footer = $('<div class="modal-footer"><button type="button" class="btn btn-primary" data-dismiss="modal">' +  $options.modalStayLoggedBtn + ' (<span id="countdowntimer">' + $countDownTimer + '</span>)</button></div>');
				} else {
					$footer = $('<div class="modal-footer"><button type="button" class="btn btn-primary" data-dismiss="modal">' +  $options.modalStayLoggedBtn + '</button></div>');
				}

				$logoutBtn = $('<button type="button" class="btn btn-default" id="logoff">' + $options.modalLogOffBtn + '</button>');

				$content.append($header, $body, $footer);
				$footer.prepend($logoutBtn);
				$dialog.append($content);
				$container.append($dialog);

				$($container).modal({
					backdrop: 'static',
					keyboard: false,
					show: true
				});

				$($container).on('hide.bs.modal', function () {
					$($container).remove();
					startTimer();

					$(document).on('focus click mousemove mousedown keyup scroll keypress', function () {
						startTimer();
					});
				});

				$($logoutBtn).on('click', function () {
					logout();
				});
			} else if ($modalUI === 'jqueryui') {
				var $jqueryLogout;
				var $jqueryModalOptions = {};
				var $jqueryModal = '<div id="notifyLogout"><p>' + $options.modalBody + '</p></div>';

				$jqueryModalOptions[$options.modalStayLoggedBtn] = function (){
					$jqueryLogout.dialog('close');
					startTimer();

					$(document).on('focus click mousemove mousedown keyup scroll keypress', function () {
						startTimer();
					});
				};

				$jqueryModalOptions[$options.modalLogOffBtn] = function (){
					logout();
				};

				$jqueryLogout = $($jqueryModal).dialog({
					buttons: $jqueryModalOptions,
					modal: true,
					width: 600,
					height: 300,
					resizable: false,
					title: $options.modalTitle
				});
			}
		};

		/**
		 * var logout -
		 *
		 * Called when the session times out and sends the user to the logout
		 * page as set in the options. It first checks if the referer settings
		 * are configured and handles the logout accordingly.
		 *
		 * @return {object} [Returns the new window location (logoff)]
		 */
		var logout = function () {
			var $referralURL;

			clearTimeout($timeoutTimer);
			clearTimeout($logoutTimer);

			if ($options.referer !== false) {
				if ($options.referer === 'auto') {
					var $currentReferral = $(location).attr('href');

					$referralURL = $options.logouturl + '?' + encodeURIComponent($options.refererName) + '=' + encodeURIComponent($currentReferral);
				} else {
					$referralURL = $options.logouturl + '?' + encodeURIComponent($options.refererName) + '=' + encodeURIComponent($options.referer);
				}
			} else {
				$referralURL = $options.logouturl;
			}

 			// Remove any handlers that would prevent us navigate away from a page. For example if the user changed a form
 			// the logout would be prevented by the "You have unsaved changes. Are you sure you want to leave?" dialog box.
 			// Unfortunately, this also means that if the user does have unsaved changes and the user is auto logged out, they will lose their changes.
      // The two features aren't compatible with each other and the security feature
 			// has to be prioritised above the convenience feature, so in that case we will log the user out.
      $(document).ready(function(){
 				$(window).unbind('beforeunload');
 			})
			return window.location.replace($referralURL);
		};

		/**
		 * Initializes the plugin.
		 */
		return this.each(function () {
			init();
		});
	};

}(jQuery, document, window));

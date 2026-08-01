odoo.define('hr_attendance_geolocation.attendance_geolocation', function (require) {
    'use strict';

    var MyAttendances = require('hr_attendance.my_attendances');
    var KioskConfirm = require('hr_attendance.kiosk_confirm');
    var core = require('web.core');
    var _t = core._t;

    MyAttendances.include({
        update_attendance: function () {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 60000,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function (position) { self._geo_manual_attendance(position); },
                    function (error) { self._geo_position_error(error); },
                    options
                );
            } else {
                this._super();
            }
        },

        _geo_manual_attendance: function (position) {
            var self = this;
            return this._rpc({
                model: 'hr.employee',
                method: 'attendance_manual',
                args: [
                    [this.employee.id],
                    'hr_attendance.hr_attendance_action_my_attendances',
                    null,
                    [position.coords.latitude, position.coords.longitude],
                ],
            }).then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.displayNotification({
                        message: result.warning,
                        type: 'warning',
                    });
                }
            }).guardedCatch(function () {
                self.displayNotification({
                    message: _t('An error occurred'),
                    type: 'danger',
                });
            });
        },

        _geo_position_error: function (error) {
            console.warn('ERROR(' + error.code + '): ' + error.message);
            var position = { coords: { latitude: 0.0, longitude: 0.0 } };
            this._geo_manual_attendance(position);
        },
    });

    KioskConfirm.include({
        start: function () {
            this._geo_pin_pad = false;
            return this._super.apply(this, arguments);
        },

        _signInOut: function () {
            this._geo_update_attendance();
        },

        _geo_update_attendance: function () {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function (position) { self._geo_kiosk_attendance(position); },
                    function (error) { self._geo_kiosk_position_error(error); },
                    options
                );
            }
        },

        _geo_kiosk_attendance: function (position) {
            var self = this;
            return this._rpc({
                model: 'hr.employee',
                method: 'attendance_manual',
                args: [
                    [this.employee_id],
                    this.next_action,
                    null,
                    [position.coords.latitude, position.coords.longitude],
                ],
            }).then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.displayNotification({
                        message: result.warning,
                        type: 'warning',
                    });
                }
            }).guardedCatch(function () {
                self.displayNotification({
                    message: _t('An error occurred'),
                    type: 'danger',
                });
            });
        },

        _geo_kiosk_position_error: function (error) {
            console.warn('ERROR(' + error.code + '): ' + error.message);
            var position = { coords: { latitude: 0.0, longitude: 0.0 } };
            this._geo_kiosk_attendance(position);
        },
    });

    return {};
});


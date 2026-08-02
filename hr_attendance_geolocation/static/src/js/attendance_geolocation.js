/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { MyAttendances } from '@hr_attendance/js/my_attendances';
import { KioskConfirm } from '@hr_attendance/js/kiosk_confirm';

patch(MyAttendances.prototype, {
    setup() {
        this._super(...arguments);
        this.location = [null, null];
        this.errorCode = null;
    },
    
    update_attendance() {
        const options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 60000,
        };
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                this._manual_attendance.bind(this),
                this._getPositionError.bind(this),
                options
            );
        }
    },
    
    async _manual_attendance(position) {
        try {
            const result = await this.env.services.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.employee.id],
                'hr_attendance.hr_attendance_action_my_attendances',
                null,
                [position.coords.latitude, position.coords.longitude]]
            );
            
            if (result.action) {
                await this.env.services.action.doAction(result.action);
            } else if (result.warning) {
                this.env.services.notification.add(result.warning, {
                    type: 'warning',
                });
            }
        } catch (error) {
            this.env.services.notification.add(_t('An error occurred'), {
                type: 'danger',
            });
            console.error(error);
        }
    },
    
    _getPositionError(error) {
        console.warn("ERROR(" + error.code + "): " + error.message);
        const position = {
            coords: {
                latitude: 0.0,
                longitude: 0.0,
            },
        };
        this._manual_attendance(position);
    },
});

patch(KioskConfirm.prototype, {
    setup() {
        this._super(...arguments);
        this.pin_pad = false;
    },
    
    onClickSignInOut() {
        this.update_attendance();
    },
    
    onClickPINpadButton() {
        this.pin_pad = true;
        this.update_attendance();
    },
    
    update_attendance() {
        const options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0,
        };
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                this._manual_attendance.bind(this),
                this._getPositionError.bind(this),
                options
            );
        }
    },
    
    async _manual_attendance(position) {
        let pinBoxVal = null;
        if (this.pin_pad) {
            const pinPadButton = document.querySelector(".o_hr_attendance_pin_pad_button_ok");
            if (pinPadButton) {
                pinPadButton.setAttribute("disabled", "disabled");
            }
            const pinBox = document.querySelector(".o_hr_attendance_PINbox");
            if (pinBox) {
                pinBoxVal = pinBox.value;
            }
        }
        
        try {
            const result = await this.env.services.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.employee_id],
                this.next_action,
                pinBoxVal,
                [position.coords.latitude, position.coords.longitude]]
            );
            
            if (result.action) {
                await this.env.services.action.doAction(result.action);
            } else if (result.warning) {
                this.env.services.notification.add(result.warning, {
                    type: 'warning',
                });
                
                if (this.pin_pad) {
                    const pinBox = document.querySelector(".o_hr_attendance_PINbox");
                    if (pinBox) {
                        pinBox.value = "";
                    }
                    
                    setTimeout(() => {
                        const pinPadButton = document.querySelector(".o_hr_attendance_pin_pad_button_ok");
                        if (pinPadButton) {
                            pinPadButton.removeAttribute("disabled");
                        }
                    }, 500);
                }
                this.pin_pad = false;
            }
        } catch (error) {
            this.env.services.notification.add(_t('An error occurred'), {
                type: 'danger',
            });
            console.error(error);
        }
    },
    
    _getPositionError(error) {
        console.warn("ERROR(" + error.code + "): " + error.message);
        const position = {
            coords: {
                latitude: 0.0,
                longitude: 0.0,
            },
        };
        this._manual_attendance(position);
    },
});


import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    DEVICE_CLASS_SPEAKER,
)
from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_STOP,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    MEDIA_TYPE_MUSIC,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
    STATE_OFF,
)
from hatch_rest_api import RestPlus, RestPlusAudioTrack, REST_PLUS_AUDIO_TRACKS, RestMini, RestMiniAudioTrack, REST_MINI_AUDIO_TRACKS
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RestMediaEntity(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_device_class = DEVICE_CLASS_SPEAKER

    def __init__(self, rest_device: RestMini | RestPlus):
        self._attr_unique_id = rest_device.thing_name
        self._attr_name = rest_device.device_name
        self.rest_device = rest_device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Hatch",
            model=rest_device.__class__.__name__,
            name=self._attr_name,
            sw_version=self.rest_device.firmware_version,
        )
        if isinstance(rest_device, RestMini):
            self._attr_sound_mode_list = list(
                map(lambda x: x.name, REST_MINI_AUDIO_TRACKS[1:])
            )
            self.none_track = RestMiniAudioTrack.NONE
            self._attr_supported_features = (
                    SUPPORT_PAUSE
                    | SUPPORT_PLAY
                    | SUPPORT_STOP
                    | SUPPORT_SELECT_SOUND_MODE
                    | SUPPORT_VOLUME_SET
                    | SUPPORT_VOLUME_STEP
            )
        else:
            self._attr_sound_mode_list = list(
                map(lambda x: x.name, REST_PLUS_AUDIO_TRACKS[1:])
            )
            self.none_track = RestPlusAudioTrack.NONE
            self._attr_supported_features = (
                    SUPPORT_PAUSE
                    | SUPPORT_PLAY
                    | SUPPORT_STOP
                    | SUPPORT_SELECT_SOUND_MODE
                    | SUPPORT_VOLUME_SET
                    | SUPPORT_VOLUME_STEP
                    | SUPPORT_TURN_ON
                    | SUPPORT_TURN_OFF
            )

        self.rest_device.register_callback(self._update_local_state)

    def replace_rest_device(self, rest_device):
        self.rest_device.remove_callback(self._update_local_state)
        self.rest_device = rest_device
        self.rest_device.register_callback(self._update_local_state)

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if isinstance(self.rest_device, RestMini) or self.rest_device.is_on:
            if self.rest_device.is_playing:
                self._attr_state = STATE_PLAYING
            else:
                self._attr_state = STATE_IDLE
        else:
            self._attr_state = STATE_OFF
        self._attr_sound_mode = self.rest_device.audio_track.name
        self._attr_volume_level = self.rest_device.volume / 100
        self._attr_device_info.update(sw_version=self.rest_device.firmware_version)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        if self.rest_device.is_playing is not None:
            self._update_local_state()

    def _find_track(self, sound_mode=None):
        if sound_mode is None:
            sound_mode = self._attr_sound_mode
        if isinstance(self.rest_device, RestMini):
            return next(
                (track for track in REST_MINI_AUDIO_TRACKS if track.name == sound_mode),
                None,
            )
        else:
            return next(
                (track for track in REST_PLUS_AUDIO_TRACKS if track.name == sound_mode),
                None,
            )

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self):
        self.rest_device.set_audio_track(self.rest_device.audio_track)

    def media_pause(self):
        self.rest_device.set_audio_track(self.none_track)

    def media_stop(self):
        self.rest_device.set_audio_track(self.none_track)

    def select_sound_mode(self, sound_mode: str):
        track = self._find_track(sound_mode=sound_mode)
        if track is None:
            track = self.none_track
        self.rest_device.set_audio_track(track)

    def turn_on(self):
        if isinstance(self.rest_device, RestMini):
            raise NotImplementedError()
        self.rest_device.set_on(True)

    def turn_off(self):
        if isinstance(self.rest_device, RestMini):
            raise NotImplementedError()
        self.rest_device.set_on(False)

-- Add a unique key on user_id/room_id, so each user can only be in a room once.
ALTER TABLE `api_membership` ADD UNIQUE INDEX `api_membership_user_room` (`user_id`, `room_id`);

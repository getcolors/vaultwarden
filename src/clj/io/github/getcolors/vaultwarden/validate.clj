(ns io.github.getcolors.vaultwarden.validate
  (:require [clojure.string :as str]
            [green.cli :as green-cli]
            [green.providers :as provider-ops]))

(def own-required
  [:vaultwarden-host :vaultwarden-image
   :vaultwarden-owner-email :vaultwarden-signups-allowed
   :vaultwarden-admin-enabled
   :litestream-r2-bucket :litestream-r2-endpoint :litestream-r2-region
   :litestream-r2-prefix :litestream-retention :litestream-snapshot-interval
   :litestream-restore-check-oncalendar])

(def own-secrets
  [:litestream-r2-access-key-id :litestream-r2-secret-access-key
   :vaultwarden-admin-token])

(def profile-par (green-cli/par-name :profile))
(def host-re #"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
(def repo-re #"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
(def official-image-re #"^ghcr\.io/getcolors/vaultwarden(?::[^@\s]+|@sha256:[0-9a-fA-F]{64})$")
(def email-re #"^[^@\s]+@[^@\s]+\.[^@\s]+$")
(def duration-re #"^[1-9][0-9]*(?:ms|s|m|h)$")

(defn placeholder? [x] (provider-ops/placeholder? x))

(defn env-errors [env]
  (when (not-empty (str (get env profile-par)))
    [(str profile-par " is set. This package takes profile from colors.yml only.")]))

(defn state-errors [opts]
  (vec
   (concat
    (for [k (concat [:profile :workdir] own-required)
          :when (placeholder? (get opts k))]
      (str k " is required"))
    (when-not (or (placeholder? (:vaultwarden-host opts))
                  (re-matches host-re (str (:vaultwarden-host opts))))
      [":vaultwarden-host must be a fully qualified hostname"])
    (when (and (placeholder? (:vaultwarden-repo opts))
               (not (re-matches official-image-re (str (:vaultwarden-image opts)))))
      [":vaultwarden-repo is required unless :vaultwarden-image uses ghcr.io/getcolors/vaultwarden with an explicit tag or digest"])
    (when (and (not (placeholder? (:vaultwarden-repo opts)))
               (not (re-matches repo-re (str (:vaultwarden-repo opts)))))
      [":vaultwarden-repo must be owner/name"])
    (when-not (or (placeholder? (:vaultwarden-owner-email opts))
                  (re-matches email-re (str (:vaultwarden-owner-email opts))))
      [":vaultwarden-owner-email must be an email address"])
    (when-not (or (placeholder? (:vaultwarden-image opts))
                  (re-find #"[:@]" (str (:vaultwarden-image opts))))
      [":vaultwarden-image must carry an explicit tag or digest"])
    (when-not (boolean? (:vaultwarden-signups-allowed opts))
      [":vaultwarden-signups-allowed must be true or false"])
    (when-not (false? (:vaultwarden-signups-allowed opts))
      [":vaultwarden-signups-allowed must remain false; bootstrap uses an invitation"])
    (when-not (false? (:vaultwarden-admin-enabled opts))
      [":vaultwarden-admin-enabled must remain false in converged desired state"])
    (for [k [:litestream-retention :litestream-snapshot-interval]
          :when (and (not (placeholder? (get opts k)))
                     (not (re-matches duration-re (str (get opts k)))))]
      (str k " must be a positive duration such as 24h"))
    (when-not (or (placeholder? (:litestream-restore-check-oncalendar opts))
                  (= "Sun *-*-* 03:00:00"
                     (str (:litestream-restore-check-oncalendar opts))))
      [":litestream-restore-check-oncalendar must be Sun *-*-* 03:00:00; the image supports one weekly restore-check schedule"]))))

(defn secret-errors [opts]
  (map #(str "required credential is not set: " (green-cli/par-name %))
       (filter #(placeholder? (get opts %)) own-secrets)))

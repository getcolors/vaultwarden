(ns io.github.getcolors.vaultwarden.tools
  (:require [io.github.getcolors.once.tools :as once-tools]
            [io.github.getcolors.vaultwarden.utils :as utils]))

(def compute-tool "tofu-compute")
(def smtp-tool "tofu-smtp")
(def dns-tool "tofu-dns")
(def smtp-post-tool "tofu-smtp-post")

(defn tool-dir [opts tool] (once-tools/tool-dir opts tool))
(defn backend-credential-env [opts] (once-tools/backend-credential-env opts))

(defn app-env [opts]
  [(str "DOMAIN=https://" (:vaultwarden-host opts))
   "DATA_FOLDER=/storage"
   "ROCKET_ADDRESS=127.0.0.1"
   "ROCKET_PORT=8080"
   (str "SIGNUPS_ALLOWED=" (:vaultwarden-signups-allowed opts))
   (str "OWNER_EMAIL=" (:vaultwarden-owner-email opts))
   (str "LITESTREAM_BUCKET=" (:litestream-r2-bucket opts))
   (str "LITESTREAM_ENDPOINT=" (:litestream-r2-endpoint opts))
   (str "LITESTREAM_REGION=" (:litestream-r2-region opts))
   (str "LITESTREAM_PREFIX=" (:litestream-r2-prefix opts))
   (str "LITESTREAM_RETENTION=" (:litestream-retention opts))
   (str "LITESTREAM_SNAPSHOT_INTERVAL=" (:litestream-snapshot-interval opts))
   (str "RESTORE_CHECK_ONCALENDAR=" (:litestream-restore-check-oncalendar opts))
   (str "LITESTREAM_ACCESS_KEY_ID=" (utils/par-lookup :litestream-r2-access-key-id))
   (str "LITESTREAM_SECRET_ACCESS_KEY=" (utils/par-lookup :litestream-r2-secret-access-key))
   (str "VAULTWARDEN_BOOTSTRAP_ADMIN_TOKEN=" (utils/par-lookup :vaultwarden-admin-token))])

(defn with-once-shape [opts]
  (let [app (cond-> {:host (:vaultwarden-host opts)
                     :image (:vaultwarden-image opts)
                     :env (app-env opts)}
              (some? (:vaultwarden-repo opts))
              (assoc :github (:vaultwarden-repo opts)))]
    (assoc opts :once {:applications [app]})))

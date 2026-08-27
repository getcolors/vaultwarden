(ns pin (:require [clojure.java.shell :as sh] [clojure.string :as str]))
;; One SHA, three payloads. Every payload is born unpinned — no invented SHAs —
;; and `bb pin` stamps or re-stamps it after a clean, pushed HEAD. Each site
;; recognises exactly two forms, its unpinned birth shape and its pinned shape,
;; and the run fails loudly when a payload matches neither.
(defn git [& args] (let [{:keys [exit out]} (apply sh/sh "git" args)] (when (zero? exit) (str/trim out))))

(defn stamp-green [s sha]
  (when (re-find #"\(def \^:private vaultwarden-sha (?:nil|\"[0-9a-f]{40}\")\)" s)
    (str/replace-first s #"\(def \^:private vaultwarden-sha (?:nil|\"[0-9a-f]{40}\")\)"
                       (str "(def ^:private vaultwarden-sha \"" sha "\")"))))

(defn stamp-red [s sha]
  (let [pinned (str "\"package-vaultwarden-red\": \"github:getcolors/vaultwarden#" sha "\",")]
    (cond (str/includes? s "\"package-vaultwarden-red\": null,")
          (str/replace-first s "\"package-vaultwarden-red\": null," pinned)
          (re-find #"\"package-vaultwarden-red\": \"github:getcolors/vaultwarden#[0-9a-f]{40}\"," s)
          (str/replace-first s #"\"package-vaultwarden-red\": \"github:getcolors/vaultwarden#[0-9a-f]{40}\"," pinned))))

(def blue-unpinned-meta "# dependencies = []\n# ///")
(defn blue-pinned-meta [sha]
  (str "# dependencies = [\"package-vaultwarden-blue\", \"blue\", \"package-once-blue\"]\n"
       "#\n"
       "# [tool.uv.sources]\n"
       "# package-vaultwarden-blue = { git = \"https://github.com/getcolors/vaultwarden.git\", rev = \"" sha "\", subdirectory = \"blue\" }\n"
       "# blue = { git = \"https://github.com/getcolors/blue.git\", rev = \"290f313ead5ca162875c33a049c880da017eae09\" }\n"
       "# package-once-blue = { git = \"https://github.com/getcolors/once.git\", subdirectory = \"blue\", rev = \"69527114b8bd1ead0b92dc1b08e6bf9a446c341a\" }\n"
       "#\n"
       ;; package-once-blue at 6952711 carries its own, older blue pin
       ;; (369c5aafea790a03b649b3513003651e672f3f57); the override makes this
       ;; package's blue pin win, as it does in blue/pyproject.toml.
       "# [tool.uv]\n"
       "# override-dependencies = [\"blue @ git+https://github.com/getcolors/blue.git@290f313ead5ca162875c33a049c880da017eae09\"]\n"
       "# ///"))
(defn stamp-blue [s sha]
  ;; First stamp is structural: the metadata block gains its git sources and the
  ;; UNPINNED paragraph collapses to a pinned-state note. Re-pinning is a SHA swap.
  (cond (str/includes? s blue-unpinned-meta)
        (-> s
            (str/replace-first blue-unpinned-meta (blue-pinned-meta sha))
            (str/replace-first #"(?s)# UNPINNED:.*?VAULTWARDEN_LIB_ROOT=/path/to/vaultwarden\n"
                               "# Stamped by `bb pin`. VAULTWARDEN_LIB_ROOT=/path/to/vaultwarden still overrides the\n# pin with a working tree.\n"))
        (re-find #"vaultwarden\.git\", rev = \"[0-9a-f]{40}\"" s)
        (str/replace-first s #"vaultwarden\.git\", rev = \"[0-9a-f]{40}\""
                           (str "vaultwarden.git\", rev = \"" sha "\""))))

(def sites
  [{:path "../skills/package-vaultwarden-green/green" :stamp stamp-green}
   {:path "../skills/package-vaultwarden-red/red" :stamp stamp-red}
   {:path "../skills/package-vaultwarden-blue/blue" :stamp stamp-blue}])

(let [dirty (git "status" "--porcelain") sha (git "rev-parse" "HEAD") remotes (git "branch" "-r" "--contains" sha)]
  (cond (seq dirty) (do (binding [*out* *err*] (println "vaultwarden working tree is dirty; commit before pinning")) (System/exit 2))
        (not (str/includes? (str remotes) "origin/")) (do (binding [*out* *err*] (println "vaultwarden HEAD is not pushed")) (System/exit 2))
        :else (let [errors (atom [])]
                (doseq [{:keys [path stamp]} sites]
                  (let [s (slurp path) n (stamp s sha)]
                    (if n (spit path n) (swap! errors conj (str "could not locate a pin form in " path)))))
                (if (seq @errors)
                  (do (binding [*out* *err*] (println (str/join "\n" @errors))) (System/exit 2))
                  (println "pinned 3 launchers to" (subs sha 0 7))))))

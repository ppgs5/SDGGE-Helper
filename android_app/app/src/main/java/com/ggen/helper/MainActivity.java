package com.ggen.helper;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Collections;

/** SD高达永恒 助手 — WebView 壳：assets 全量离线（含 SQLite + sql.js + 全部图片）
 *  在线更新：Android 桥（window.Android）在 Java 侧下载新数据库到内部存储；
 *  下载后的库优先于 assets 内置库被加载（shouldInterceptRequest 拦截 data/ggen.db）。 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.local";
    private WebView web;
    private volatile String dlState = "idle";   // idle | downloading | done | error
    private volatile int dlPct = 0;
    private volatile String dlErr = "";
    /* APP 自更新: 新版本 APK 下载(DownloadManager) → 系统安装界面 */
    private volatile String apkState = "idle";  // idle | downloading | installing | error
    private volatile int apkPct = 0;
    private volatile String apkErr = "";
    private long apkDlId = -1;
    private String apkUrl2 = "", apkVer = "";
    private BroadcastReceiver apkRcv;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setSupportZoom(false);
        s.setTextZoom(100);
        web.setBackgroundColor(0xFF070B14);
        web.setWebViewClient(new LocalClient());
        web.setWebChromeClient(new WebChromeClient());
        web.addJavascriptInterface(new Bridge(), "Android");
        setContentView(web);
        web.loadUrl("https://" + HOST + "/index.html");
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript(
            "(window.__appBack && window.__appBack()) ? '1' : '0'",
            value -> { if (!"\"1\"".equals(value)) MainActivity.super.onBackPressed(); });
    }

    private File customDb() { return new File(getFilesDir(), "ggen.db"); }

    private File patchDir() {
        File d = new File(getFilesDir(), "patches");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    private File imageDir() {
        File d = new File(getFilesDir(), "img");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    /** JS 桥：检查/下载/删除自定义数据库 */
    private class Bridge {
        @JavascriptInterface
        public String dbInfo() {
            JSONObject o = new JSONObject();
            try {
                File f = customDb();
                o.put("custom", f.exists());
                o.put("size", f.length());
            } catch (Exception ignored) {}
            return o.toString();
        }

        @JavascriptInterface
        public String appInfo() {
            JSONObject o = new JSONObject();
            try {
                o.put("versionCode", getPackageManager().getPackageInfo(getPackageName(), 0).versionCode);
                o.put("versionName", getPackageManager().getPackageInfo(getPackageName(), 0).versionName);
            } catch (Exception ignored) {}
            return o.toString();
        }

        @JavascriptInterface
        public boolean downloadApk(final String url, final String url2, final String version) {
            if ("downloading".equals(apkState)) return false;
            apkState = "downloading"; apkPct = 0; apkErr = "";
            apkUrl2 = url2 == null ? "" : url2;
            apkVer = version == null ? "new" : version;
            enqueueApk(url);
            return true;
        }

        private void enqueueApk(String url) {
            try {
                DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.setMimeType("application/vnd.android.package-archive");
                req.setTitle("SD高达永恒助手 v" + apkVer);
                req.setDescription("正在下载新版本（完成后弹出安装界面）");
                req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                req.setDestinationInExternalFilesDir(MainActivity.this, Environment.DIRECTORY_DOWNLOADS, "SD高达永恒助手-v" + apkVer + ".apk");
                apkDlId = dm.enqueue(req);
                if (apkRcv == null) {
                    apkRcv = new BroadcastReceiver() {
                        @Override public void onReceive(Context c, Intent i) {
                            long id = i.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                            if (id != apkDlId) return;
                            DownloadManager dm2 = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                            int st = -1;
                            try (Cursor cur = dm2.query(new DownloadManager.Query().setFilterById(id))) {
                                if (cur.moveToFirst()) st = cur.getInt(cur.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
                            } catch (Exception ignored) {}
                            if (st == DownloadManager.STATUS_SUCCESSFUL) {
                                apkPct = 100; apkState = "installing";
                                Intent it = new Intent(Intent.ACTION_VIEW);
                                it.setDataAndType(dm2.getUriForDownloadedFile(id), "application/vnd.android.package-archive");
                                it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                                try { startActivity(it); }
                                catch (Exception e) { apkErr = "请到通知栏或「下载」目录手动安装"; apkState = "error"; }
                                return;
                            }
                            if (st == DownloadManager.STATUS_FAILED && !apkUrl2.isEmpty()) {   // 镜像兜底重试
                                String u2 = apkUrl2; apkUrl2 = "";
                                enqueueApk(u2);
                                return;
                            }
                            apkErr = "下载失败，请检查网络后重试"; apkState = "error";
                        }
                    };
                    IntentFilter f = new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE);
                    if (Build.VERSION.SDK_INT >= 33) registerReceiver(apkRcv, f, Context.RECEIVER_EXPORTED);
                    else registerReceiver(apkRcv, f);
                }
            } catch (Exception e) {
                apkErr = String.valueOf(e.getMessage()); apkState = "error";
            }
        }

        @JavascriptInterface
        public void openUrl(String url) {
            try {
                Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
            } catch (Exception ignored) {}
        }

        @JavascriptInterface
        public String apkState() {
            JSONObject o = new JSONObject();
            try {
                o.put("state", apkState); o.put("pct", apkPct); o.put("err", apkErr);
                if (apkDlId > 0 && "downloading".equals(apkState)) {
                    DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                    try (Cursor cur = dm.query(new DownloadManager.Query().setFilterById(apkDlId))) {
                        if (cur.moveToFirst()) {
                            long tot = cur.getLong(cur.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES));
                            long got = cur.getLong(cur.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
                            if (tot > 0) { apkPct = (int) (got * 100 / tot); o.put("pct", apkPct); }
                        }
                    } catch (Exception ignored) {}
                }
            } catch (Exception ignored) {}
            return o.toString();
        }

        @JavascriptInterface
        public boolean downloadDb(final String url, final String sha256) {
            if ("downloading".equals(dlState)) return false;
            dlState = "downloading"; dlPct = 0; dlErr = "";
            new Thread(() -> {
                File tmp = new File(getFilesDir(), "ggen.db.tmp");
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                    c.setInstanceFollowRedirects(true);
                    c.setConnectTimeout(20000);
                    c.setReadTimeout(60000);
                    c.setRequestProperty("User-Agent", "ggen-helper-updater");
                    int code = c.getResponseCode();
                    if (code != 200) throw new IOException("HTTP " + code);
                    long total = c.getContentLengthLong();
                    MessageDigest md = MessageDigest.getInstance("SHA-256");
                    long got = 0;
                    try (InputStream in = c.getInputStream(); FileOutputStream out = new FileOutputStream(tmp)) {
                        byte[] buf = new byte[65536];
                        int n;
                        while ((n = in.read(buf)) > 0) {
                            out.write(buf, 0, n);
                            md.update(buf, 0, n);
                            got += n;
                            if (total > 0) dlPct = (int) (got * 100 / total);
                        }
                    }
                    if (sha256 != null && sha256.length() > 0) {
                        StringBuilder hex = new StringBuilder();
                        for (byte b : md.digest()) hex.append(String.format("%02x", b));
                        if (!hex.toString().equalsIgnoreCase(sha256)) throw new IOException("SHA-256 校验失败，文件可能损坏");
                    }
                    File dst = customDb();
                    if (dst.exists() && !dst.delete()) throw new IOException("无法替换旧数据库");
                    if (!tmp.renameTo(dst)) throw new IOException("保存失败");
                    dlPct = 100;
                    dlState = "done";
                } catch (Exception e) {
                    tmp.delete();
                    dlErr = String.valueOf(e.getMessage());
                    dlState = "error";
                }
            }).start();
            return true;
        }

        @JavascriptInterface
        public String updateState() {
            JSONObject o = new JSONObject();
            try {
                o.put("state", dlState);
                o.put("pct", dlPct);
                o.put("err", dlErr);
            } catch (Exception ignored) {}
            return o.toString();
        }

        @JavascriptInterface
        public void deleteDb() {
            File f = customDb();
            if (f.exists()) f.delete();
            dlState = "idle"; dlPct = 0; dlErr = "";
        }

        /* ---- 增量补丁文件（名称形如 p_<built_at>.sql） ---- */

        @JavascriptInterface
        public String listPatches() {
            org.json.JSONArray arr = new org.json.JSONArray();
            try {
                String[] names = patchDir().list();
                if (names != null) {
                    java.util.Arrays.sort(names);
                    for (String n : names) if (n.endsWith(".sql")) arr.put(n);
                }
            } catch (Exception ignored) {}
            return arr.toString();
        }

        @JavascriptInterface
        public String readPatch(String name) {
            if (!safeName(name)) return "";
            try {
                byte[] b = new byte[(int) new File(patchDir(), name).length()];
                try (FileInputStream in = new FileInputStream(new File(patchDir(), name))) {
                    int off = 0, n;
                    while (off < b.length && (n = in.read(b, off, b.length - off)) > 0) off += n;
                }
                return new String(b, "UTF-8");
            } catch (Exception e) {
                return "";
            }
        }

        @JavascriptInterface
        public boolean savePatch(String name, String content) {
            if (!safeName(name)) return false;
            try {
                File tmp = new File(patchDir(), name + ".tmp");
                try (FileOutputStream out = new FileOutputStream(tmp)) {
                    out.write(content.getBytes("UTF-8"));
                }
                File dst = new File(patchDir(), name);
                if (dst.exists()) dst.delete();
                return tmp.renameTo(dst);
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public void deletePatch(String name) {
            if (!safeName(name)) return;
            new File(patchDir(), name).delete();
        }

        @JavascriptInterface
        public void clearPatches() {
            File[] fs = patchDir().listFiles();
            if (fs != null) for (File f : fs) f.delete();
        }

        private boolean safeName(String n) {
            return n != null && n.length() > 0 && n.length() < 128 && n.matches("[A-Za-z0-9_.-]+");
        }

        /* ---- 增量头像图片（名称形如 thumb/thum_xxx.webp 或 item/xxx.webp, base64 传入） ---- */

        @JavascriptInterface
        public boolean saveImage(String name, String base64) {
            if (!safeImageName(name) || base64 == null) return false;
            try {
                byte[] data = android.util.Base64.decode(base64, android.util.Base64.DEFAULT);
                File dst = new File(imageDir(), name);
                File parent = dst.getParentFile();
                if (parent != null && !parent.exists()) parent.mkdirs();
                File tmp = new File(dst.getPath() + ".tmp");
                try (FileOutputStream out = new FileOutputStream(tmp)) {
                    out.write(data);
                }
                if (dst.exists()) dst.delete();
                return tmp.renameTo(dst);
            } catch (Exception e) {
                return false;
            }
        }

        @JavascriptInterface
        public void clearImages() {
            deleteRec(imageDir());
        }

        private void deleteRec(File f) {
            File[] fs = f.listFiles();
            if (fs != null) for (File c : fs) deleteRec(c);
            f.delete();
        }

        private boolean safeImageName(String n) {
            return n != null && n.matches("(thumb|item)/[A-Za-z0-9_.-]+\\.webp") && !n.contains("..");
        }
    }

    private class LocalClient extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
            if (!HOST.equals(req.getUrl().getHost())) return null;
            String path = req.getUrl().getPath();
            if (path == null || path.equals("/")) path = "/index.html";
            String asset = path.startsWith("/") ? path.substring(1) : path;
            try {
                if (asset.equals("data/ggen.db")) {          // 已下载的更新库优先于内置库
                    File f = customDb();
                    if (f.exists()) return new WebResourceResponse("application/octet-stream", null, new FileInputStream(f));
                }
                if (asset.startsWith("img/")) {              // 增量同步的头像优先于内置资源
                    File f = new File(imageDir(), asset.substring(4));
                    if (f.exists()) return new WebResourceResponse(mime(asset), null, new FileInputStream(f));
                }
                InputStream is = getAssets().open(asset);
                return new WebResourceResponse(mime(asset), null, is);
            } catch (IOException e) {
                return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found",
                        Collections.emptyMap(), new ByteArrayInputStream(("404 " + asset).getBytes()));
            }
        }
    }

    private static String mime(String p) {
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js")) return "application/javascript";
        if (p.endsWith(".css")) return "text/css";
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".webp")) return "image/webp";
        return "application/octet-stream";
    }
}

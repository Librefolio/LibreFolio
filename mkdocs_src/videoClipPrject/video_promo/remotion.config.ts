// video_promo/remotion.config.ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setCodec("h264");
Config.setScale(2); // output 2x per qualità 2K/4K

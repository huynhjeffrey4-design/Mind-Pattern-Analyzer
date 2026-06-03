import { Router, type IRouter } from "express";
import healthRouter from "./health";
import checkinsRouter from "./checkins";
import journalRouter from "./journal";
import insightsRouter from "./insights";

const router: IRouter = Router();

router.use(healthRouter);
router.use(checkinsRouter);
router.use(journalRouter);
router.use(insightsRouter);

export default router;

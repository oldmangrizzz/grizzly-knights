import { mutation } from './_generated/server';
import { v } from 'convex/values';
import { WorldMap } from './aiTown/worldMap';
import * as mapData from '../data/gentle';

export const forceUpdateMap = mutation({
  args: {},
  handler: async (ctx) => {
    const worldStatus = await ctx.db
      .query('worldStatus')
      .filter((q) => q.eq(q.field('isDefault'), true))
      .first();
    if (!worldStatus) {
      throw new Error('No default world found');
    }

    const map = await ctx.db
      .query('maps')
      .withIndex('worldId', (q) => q.eq('worldId', worldStatus.worldId))
      .unique();

    if (!map) {
      throw new Error(`No map found for world ${worldStatus.worldId}`);
    }

    console.log(`Updating map for world ${worldStatus.worldId} to use ${mapData.tilesetpath}`);

    await ctx.db.patch(map._id, {
      tileSetUrl: mapData.tilesetpath,
      tileSetDimX: mapData.tilesetpxw,
      tileSetDimY: mapData.tilesetpxh,
      tileDim: mapData.tiledim,
    });
    
    return { success: true, path: mapData.tilesetpath };
  },
});

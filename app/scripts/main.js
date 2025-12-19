import { world, system } from "@minecraft/server";

// 設定：一度に壊せる最大ブロック数
const MAX_BREAK_LIMIT = 300;

// ブロック破壊イベントを監視
world.afterEvents.playerBreakBlock.subscribe((event) => {
    const { block, player } = event;

    // --- 重要：スニーク判定 ---
    // プレイヤーがしゃがんでいる(isSneakingがtrue)場合は、
    // ここで処理を終了（return）させることで、一括破壊を発動させません。
    if (player.isSneaking) return;

    // 最初に壊したのが「木材的なもの」かチェック
    // 通常の原木(_log) または ネザーの幹(_stem)
    const isLog = block.typeId.includes("_log") || block.typeId.includes("_stem");
    
    // 木でなければ何もしない
    if (!isLog) return;

    // 一括破壊を開始
    breakTree(block.location, block.typeId, block.dimension, player);
});

// 木と葉（およびネザーの構成ブロック）を破壊してアイテムを引き寄せる関数
function breakTree(startPos, logTypeId, dimension, player) {
    let queue = [startPos];
    let visited = new Set();
    visited.add(`${startPos.x},${startPos.y},${startPos.z}`);

    let breakCount = 0;

    system.run(() => {
        while (queue.length > 0 && breakCount < MAX_BREAK_LIMIT) {
            let current = queue.shift();

            // 全26方向（斜め含む）をチェック
            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dz = -1; dz <= 1; dz++) {
                        // 自分自身はスキップ
                        if (dx === 0 && dy === 0 && dz === 0) continue;

                        const nextPos = {
                            x: current.x + dx,
                            y: current.y + dy,
                            z: current.z + dz
                        };
                        const key = `${nextPos.x},${nextPos.y},${nextPos.z}`;

                        if (!visited.has(key)) {
                            try {
                                const nextBlock = dimension.getBlock(nextPos);
                                if (!nextBlock) continue;

                                const type = nextBlock.typeId;

                                // --- 破壊対象の判定 ---
                                
                                // 1. 幹（ログ）の判定
                                // 最初に壊したものと同じ種類の原木・幹であること
                                const isTargetLog = type === logTypeId;

                                // 2. 葉っぱ・ウォートブロック・シュルームライトの判定
                                const isLeafLike = type.includes("_leaves") || 
                                                   type.includes("wart_block") || 
                                                   type === "minecraft:shroomlight";

                                if (isTargetLog || isLeafLike) {
                                    // 破壊処理 (destroyでアイテム化)
                                    dimension.runCommand(`setblock ${nextPos.x} ${nextPos.y} ${nextPos.z} air [] destroy`);
                                    
                                    // アイテム吸い寄せ (半径4ブロック以内のアイテムをプレイヤーへ)
                                    try {
                                        player.runCommand(`execute at ${nextPos.x} ${nextPos.y} ${nextPos.z} run tp @e[type=item, r=4] @s`);
                                    } catch (e) {
                                        // アイテムがない場合のエラーは無視
                                    }

                                    // 次の探索へ
                                    queue.push(nextPos);
                                    visited.add(key);
                                    breakCount++;
                                }
                            } catch (e) {
                                // 読み込みエラー等は無視
                            }
                        }
                    }
                }
            }
        }
    });
}
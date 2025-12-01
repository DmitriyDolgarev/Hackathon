print("=" * 80)
print("ПОЛНЫЙ ЦИКЛ: ЛИНИИ МАРШРУТОВ → ПОЛИГОНЫ ИЗОХРОН")
print("=" * 80)

from qgis.core import *
import processing
import math
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

# Координаты Иркутска
LON = 104.261370
LAT = 52.262468

def full_isochrone_pipeline():
    """Полный цикл создания изохрон: линии → полигоны"""
    
    print("🔍 Проверка данных...")
    
    # 1. Проверяем слой дорог
    roads = iface.activeLayer()
    if not roads or roads.geometryType() != QgsWkbTypes.LineGeometry:
        print("❌ Нет линейного слоя дорог!")
        print("Загрузите УДС_link.shp и сделайте его активным")
        return
    
    print(f"✅ Дороги: {roads.name()} ({roads.featureCount()} сегментов)")
    
    # 2. Преобразуем координаты
    print(f"\n📍 Преобразование координат...")
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    roads_crs = roads.crs()
    
    try:
        transform = QgsCoordinateTransform(wgs84, roads_crs, QgsProject.instance())
        point_wgs84 = QgsPointXY(LON, LAT)
        point = transform.transform(point_wgs84)
        
        print(f"   WGS84: {LON:.6f}, {LAT:.6f}")
        print(f"   {roads_crs.authid()}: {point.x():.2f}, {point.y():.2f}")
        
    except Exception as e:
        print(f"❌ Ошибка преобразования: {e}")
        return
    
    # 3. Параметры
    speed_kmh = 5
    time_intervals = [5, 10, 15]
    
    print(f"\n📊 Параметры расчета:")
    print(f"   Скорость: {speed_kmh} км/ч (пешком)")
    print(f"   Интервалы: {time_intervals} минут")
    
    # 4. Очистка старых слоев
    print(f"\n🗑️ Очистка старых данных...")
    layers_to_remove = []
    for layer in QgsProject.instance().mapLayers().values():
        if any(keyword in layer.name() for keyword in ['Линии', 'Полигон', 'Изохрона', 'Точка']):
            layers_to_remove.append(layer.id())
    
    for layer_id in layers_to_remove:
        QgsProject.instance().removeMapLayer(layer_id)
    
    print(f"   Удалено слоев: {len(layers_to_remove)}")
    
    # 5. Создаем точку старта
    print(f"\n📍 Создание точки старта...")
    point_layer = QgsVectorLayer(f"Point?crs={roads_crs.authid()}", "Точка старта", "memory")
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(point))
    point_layer.dataProvider().addFeatures([feat])
    
    # Стиль точки
    symbol = QgsMarkerSymbol.createSimple({
        'color': '255,0,0',
        'size': '6',
        'outline_color': '255,255,255',
        'outline_width': '1.5'
    })
    point_layer.renderer().setSymbol(symbol)
    QgsProject.instance().addMapLayer(point_layer)
    print(f"   ✅ Точка создана")
    
    # 6. СОЗДАЕМ ЛИНИИ МАРШРУТОВ И ИЗВЛЕКАЕМ КРАЙНИЕ ТОЧКИ
    print(f"\n" + "-" * 40)
    print("ЭТАП 1: СОЗДАНИЕ ЛИНИЙ МАРШРУТОВ И ИЗВЛЕЧЕНИЕ КРАЙНИХ ТОЧЕК")
    print("-" * 40)
    
    line_layers = []

    end_points_five = []
    end_points_ten = []
    end_points_fiveteen = []
    
    for time_min in time_intervals:
        print(f"\n⏱️  {time_min} минут:")
        
        distance_m = (speed_kmh * 1000 / 3600) * (time_min * 60)
        print(f"   Расстояние: {distance_m:.0f} м")
        
        # Пробуем алгоритм
        print(f"   🔄 Создание линий...")
        
        params = {
            'INPUT': roads,
            'START_POINTS': point_layer,
            'TRAVEL_COST': distance_m,
            'STRATEGY': 0,  # 0 = Shortest distance
            'TOLERANCE': 50,
            'OUTPUT_LINES': 'memory:',
            'OUTPUT': 'memory:'
        }
        
        try:
            # Пробуем разные алгоритмы
            algorithms = ['qgis:serviceareafromlayer', 'native:serviceareafrompoint']
            
            lines_created = False
            for algorithm in algorithms:
                try:
                    result = processing.run(algorithm, params)
                    
                    if 'OUTPUT_LINES' in result and result['OUTPUT_LINES']:
                        lines = result['OUTPUT_LINES']
                        if lines.featureCount() > 0:
                            lines.setName(f"Линии_{time_min}мин")
                            
                            # Стиль
                            if time_min == 5:
                                line_color = "255,255,0"
                            elif time_min == 10:
                                line_color = "255,165,0"
                            else:
                                line_color = "255,0,0"
                            
                            line_symbol = QgsLineSymbol.createSimple({
                                'color': line_color,
                                'width': '0.8',
                                'style': 'solid'
                            })
                            lines.renderer().setSymbol(line_symbol)
                            
                            QgsProject.instance().addMapLayer(lines)
                            line_layers.append(lines)
                            print(f"   ✅ Линии созданы: {lines.featureCount()} сегментов")
                            
                            # Счетчики для отладки
                            total_segments = 0
                            end_points_added = 0
                            
                            # ИЗВЛЕКАЕМ ТОЛЬКО КРАЙНИЕ ТОЧКИ
                            print(f"   📍 Извлечение КРАЙНИХ точек маршрутов...")
                            
                            for feature in lines.getFeatures():
                                geom = feature.geometry()
                                
                                if geom and not geom.isEmpty():
                                    # Для MultiLineString (несколько линий)
                                    if geom.isMultipart():
                                        multi_line = geom.asMultiPolyline()
                                        total_segments += len(multi_line)
                                        
                                        # Для каждого сегмента берем ТОЛЬКО последнюю точку
                                        for line in multi_line:
                                            if len(line) >= 2:
                                                # Берем ПОСЛЕДНЮЮ точку каждой линии
                                                last_point = line[-1]
                                                if time_min == 5:
                                                    end_points_five.append(last_point)
                                                elif time_min == 10:
                                                    end_points_ten.append(last_point)
                                                else:
                                                    end_points_fiveteen.append(last_point)
                                                end_points_added += 1
                                                print(f"      Добавлена точка: {last_point.x():.2f}, {last_point.y():.2f}")
                                    else:
                                        # Для простой LineString
                                        line_pts = geom.asPolyline()
                                        total_segments += 1
                                        
                                        if len(line_pts) >= 2:
                                            # Берем ПОСЛЕДНЮЮ точку линии
                                            last_point = line_pts[-1]
                                            if time_min == 5:
                                                end_points_five.append(last_point)
                                            elif time_min == 10:
                                                end_points_ten.append(last_point)
                                            else:
                                                end_points_fiveteen.append(last_point)
                                            end_points_added += 1
                                            print(f"      Добавлена точка: {last_point.x():.2f}, {last_point.y():.2f}")
                            
                            print(f"   📊 Сегментов: {total_segments}, КРАЙНИХ точек добавлено: {end_points_added}")
                            
                            lines_created = True
                            break  # Выходим из цикла алгоритмов
                            
                except Exception as e:
                    print(f"   ⚠️ Алгоритм {algorithm} не сработал: {e}")
                    continue
            
            if not lines_created:
                print(f"   ⚠️ Не удалось создать линии, пропускаю")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    print(f"\n📊 ИТОГО собрано КРАЙНИХ точек:")
    print(f"   5 минут: {len(end_points_five)} точек")
    print(f"   10 минут: {len(end_points_ten)} точек")
    print(f"   15 минут: {len(end_points_fiveteen)} точек")

    # 7. СОЗДАЕМ ПОЛИГОНЫ ИЗ КРАЙНИХ ТОЧЕК
    print(f"\n" + "-" * 40)
    print("ЭТАП 2: СОЗДАНИЕ ПОЛИГОНОВ ИЗ КРАЙНИХ ТОЧЕК")
    print("-" * 40)

    def create_polygon_from_end_points(points, name, color, border_color):
        """Создает ЕДИНЫЙ полигон из списка КРАЙНИХ точек"""
        
        if len(points) < 3:
            print(f"⚠️ Недостаточно КРАЙНИХ точек для полигона {name} ({len(points)} точек)")
            return None
        
        print(f"   🔷 Создание полигона {name} из {len(points)} крайних точек...")
        
        # 1. Создаем временный слой точек
        temp_layer = QgsVectorLayer(f"Point?crs={roads_crs.authid()}", f"temp_{name}", "memory")
        provider = temp_layer.dataProvider()
        
        features = []
        for point in points:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(point))
            features.append(feat)
        
        provider.addFeatures(features)
        temp_layer.updateExtents()
        
        # 2. Создаем ЕДИНУЮ выпуклую оболочку всех точек
        print(f"   📐 Создание выпуклой оболочки...")
        
        # Используем dissolve, чтобы объединить все точки перед созданием оболочки
        dissolve_params = {
            'INPUT': temp_layer,
            'FIELD': [],
            'OUTPUT': 'memory:'
        }
        dissolved = processing.run("native:dissolve", dissolve_params)['OUTPUT']
        
        # Создаем выпуклую оболочку из объединенного слоя
        convex_params = {'INPUT': dissolved, 'OUTPUT': 'memory:'}
        convex_layer = processing.run("native:convexhull", convex_params)['OUTPUT']
        
        if convex_layer.featureCount() == 0:
            print(f"   ❌ Не удалось создать выпуклую оболочку для {name}")
            return None
        
        # 3. Создаем финальный полигонный слой с ЕДИНЫМ объектом
        polygon_layer = QgsVectorLayer(f"Polygon?crs={roads_crs.authid()}", name, "memory")
        polygon_provider = polygon_layer.dataProvider()
        
        polygon_provider.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("name", QVariant.String),
            QgsField("time_min", QVariant.Int),
            QgsField("points_count", QVariant.Int),
            QgsField("area_m2", QVariant.Double)
        ])
        polygon_layer.updateFields()
        
        # Получаем геометрию из выпуклой оболочки
        convex_features = list(convex_layer.getFeatures())
        if len(convex_features) > 0:
            polygon_geom = convex_features[0].geometry()
            
            # Проверяем и исправляем геометрию один раз
            if not polygon_geom.isGeosValid():
                print(f"   ⚠️ Геометрия требует исправления...")
                polygon_geom = polygon_geom.makeValid()
            
            # Рассчитываем площадь
            area_calc = QgsDistanceArea()
            area_calc.setSourceCrs(roads_crs, QgsProject.instance().transformContext())
            area_calc.setEllipsoid(roads_crs.ellipsoidAcronym())
            area_m2 = area_calc.measureArea(polygon_geom)
            
            # Определяем время по имени
            time_min = 5 if "5мин" in name else (10 if "10мин" in name else 15)
            
            # Создаем единственный объект
            feat = QgsFeature()
            feat.setGeometry(polygon_geom)
            feat.setAttributes([1, name, time_min, len(points), area_m2])
            polygon_provider.addFeatures([feat])
        
        polygon_layer.updateExtents()
        
        # 4. Применяем стиль
        symbol = QgsFillSymbol.createSimple({
            'color': color,
            'color_border': border_color,
            'width_border': '1.5',
            'style': 'solid'
        })
        polygon_layer.renderer().setSymbol(symbol)
        
        # 5. Добавляем подписи
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = 'concat("name", \' (\', round("area_m2"), \' м²)\')'
        label_settings.isExpression = True
        
        text_format = QgsTextFormat()
        text_format.setSize(10)
        text_format.setColor(QColor("white"))
        text_format.buffer().setEnabled(True)
        text_format.buffer().setColor(QColor("black"))
        text_format.buffer().setSize(2)
        
        label_settings.setFormat(text_format)
        label_settings.enabled = True
        
        layer_labeling = QgsVectorLayerSimpleLabeling(label_settings)
        polygon_layer.setLabeling(layer_labeling)
        polygon_layer.setLabelsEnabled(True)
        
        print(f"   ✅ Полигон {name} создан: 1 объект, площадь: {area_m2:.0f} м²")
        return polygon_layer
    
    def create_combined_point_layer(points_dict):
        """Создает объединенный слой всех КРАЙНИХ точек"""
        
        # Подготавливаем все точки
        all_points = []
        for time_min, points in points_dict.items():
            for point in points:
                all_points.append({
                    'point': point,
                    'time': time_min,
                    'color': get_color_for_time(time_min),
                    'label': f"{time_min} мин"
                })
        
        if not all_points:
            print("⚠️ Нет КРАЙНИХ точек для отображения")
            return None
        
        # Создаем слой
        layer = QgsVectorLayer(f"Point?crs={roads_crs.authid()}", "Все_крайние_точки", "memory")
        provider = layer.dataProvider()
        
        # Добавляем поля
        provider.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("time_min", QVariant.Int),
            QgsField("x", QVariant.Double),
            QgsField("y", QVariant.Double),
            QgsField("color", QVariant.String)
        ])
        layer.updateFields()
        
        # Создаем объекты
        features = []
        for i, item in enumerate(all_points):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(item['point']))
            feat.setAttributes([
                i + 1,
                item['time'],
                item['point'].x(),
                item['point'].y(),
                item['color']
            ])
            features.append(feat)
        
        provider.addFeatures(features)
        layer.updateExtents()
        
        # Создаем категорированный стиль
        categories = []
        
        for time_min in [5, 10, 15]:
            if time_min == 5:
                color = "0,0,255"
                symbol = QgsMarkerSymbol.createSimple({
                    'color': color,
                    'size': '6',
                    'outline_color': '255,255,255',
                    'outline_width': '1.5',
                    'name': 'circle'
                })
            elif time_min == 10:
                color = "0,255,0"
                symbol = QgsMarkerSymbol.createSimple({
                    'color': color,
                    'size': '6',
                    'outline_color': '255,255,255',
                    'outline_width': '1.5',
                    'name': 'square'
                })
            else:
                color = "255,0,0"
                symbol = QgsMarkerSymbol.createSimple({
                    'color': color,
                    'size': '6',
                    'outline_color': '255,255,255',
                    'outline_width': '1.5',
                    'name': 'triangle'
                })
            
            category = QgsRendererCategory(
                time_min,
                symbol,
                f"{time_min} минут"
            )
            categories.append(category)
        
        # Применяем категорированный рендерер
        renderer = QgsCategorizedSymbolRenderer("time_min", categories)
        layer.setRenderer(renderer)
        
        # Включаем подписи
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = 'concat("id", \' (\', "time_min", \' мин)\')'
        label_settings.isExpression = True
        
        text_format = QgsTextFormat()
        text_format.setSize(8)
        text_format.setColor(QColor("black"))
        
        label_settings.setFormat(text_format)
        label_settings.enabled = True
        
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        layer.setLabelsEnabled(True)
        
        return layer
    
    def get_color_for_time(time_min):
        """Возвращает цвет для времени"""
        if time_min == 5:
            return "0,0,255"
        elif time_min == 10:
            return "0,255,0"
        else:
            return "255,0,0"

    # Создаем объединенный слой КРАЙНИХ точек
    print(f"📍 Создание объединенного слоя КРАЙНИХ точек...")
    points_dict = {
        5: end_points_five if end_points_five else [],
        10: end_points_ten if end_points_ten else [],
        15: end_points_fiveteen if end_points_fiveteen else []
    }

    combined_layer = create_combined_point_layer(points_dict)
    if combined_layer:
        QgsProject.instance().addMapLayer(combined_layer)
        print(f"✅ Объединенный слой КРАЙНИХ точек создан: {combined_layer.featureCount()} точек")

    # Создаем полигоны из КРАЙНИХ точек
    polygon_layers = []
    
    # 1. Полигон для 5 минут
    if len(end_points_five) >= 3:
        print("\n🔷 Создание полигона для 5 минут из КРАЙНИХ точек...")
        polygon_five = create_polygon_from_end_points(
            end_points_five,  # НЕ замыкаем! Функция сама создаст выпуклую оболочку
            "Изохрона_5мин",
            "255,255,0,80",      # Желтый с прозрачностью
            "255,200,0"         # Оранжевая граница
        )
        if polygon_five:
            QgsProject.instance().addMapLayer(polygon_five)
            polygon_layers.append(polygon_five)
            print(f"✅ Полигон 5 мин создан")
    else:
        print("⚠️ Недостаточно КРАЙНИХ точек для полигона 5 минут")

    # 2. Полигон для 10 минут
    if len(end_points_ten) >= 3:
        print("\n🔷 Создание полигона для 10 минут из КРАЙНИХ точек...")
        polygon_ten = create_polygon_from_end_points(
            end_points_ten,
            "Изохрона_10мин",
            "255,165,0,100",    # Оранжевый с прозрачностью
            "255,100,0"         # Темно-оранжевая граница
        )
        if polygon_ten:
            QgsProject.instance().addMapLayer(polygon_ten)
            polygon_layers.append(polygon_ten)
            print(f"✅ Полигон 10 мин создан")
    else:
        print("⚠️ Недостаточно КРАЙНИХ точек для полигона 10 минут")

    # 3. Полигон для 15 минут
    if len(end_points_fiveteen) >= 3:
        print("\n🔷 Создание полигона для 15 минут из КРАЙНИХ точек...")
        polygon_fifteen = create_polygon_from_end_points(
            end_points_fiveteen,
            "Изохрона_15мин",
            "255,0,0,120",       # Красный с прозрачностью
            "200,0,0"            # Темно-красная граница
        )
        if polygon_fifteen:
            QgsProject.instance().addMapLayer(polygon_fifteen)
            polygon_layers.append(polygon_fifteen)
            print(f"✅ Полигон 15 мин создан")
    else:
        print("⚠️ Недостаточно КРАЙНИХ точек для полигона 15 минут")

    # 8. Финальные действия
    print(f"\n" + "-" * 40)
    print("ЭТАП 3: ФИНАЛИЗАЦИЯ")
    print("-" * 40)
    
    # Принудительно обновляем карту
    iface.mapCanvas().refresh()
    
    # Убеждаемся, что все полигоны видны
    for layer in polygon_layers:
        layer_node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(True)
    
    # Масштабируем карту
    if polygon_layers:
        combined_extent = None
        for layer in polygon_layers:
            if combined_extent is None:
                combined_extent = layer.extent()
            else:
                combined_extent.combineExtentWith(layer.extent())
        
        if combined_extent:
            # Добавляем точку
            point_extent = QgsRectangle(point.x() - 50, point.y() - 50, 
                                       point.x() + 50, point.y() + 50)
            combined_extent.combineExtentWith(point_extent)
            
            # Расширяем
            width = combined_extent.width() * 0.1
            height = combined_extent.height() * 0.1
            
            combined_extent.setXMinimum(combined_extent.xMinimum() - width)
            combined_extent.setXMaximum(combined_extent.xMaximum() + width)
            combined_extent.setYMinimum(combined_extent.yMinimum() - height)
            combined_extent.setYMaximum(combined_extent.yMaximum() + height)
            
            iface.mapCanvas().setExtent(combined_extent)
            iface.mapCanvas().refresh()
    
    print(f"\n" + "=" * 80)
    print("✅ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН!")
    print("=" * 80)
    print("Создано:")
    print("  🔴 Точка старта")
    print("  📍 Линии маршрутов")
    print("  🔵 Слой КРАЙНИХ точек маршрутов")
    print("  🟡 Полигоны изохрон из КРАЙНИХ точек")
    print(f"\n📍 Точка: {LAT:.6f}°N, {LON:.6f}°E")
    print(f"🚶 Скорость: {speed_kmh} км/ч")
    print(f"⏱️  Времена: {', '.join(str(t) for t in time_intervals)} мин")
    print("=" * 80)
    
    # Дополнительная проверка
    print(f"\n🔍 Проверка созданных слоев:")
    layer_count = 0
    for layer in QgsProject.instance().mapLayers().values():
        if any(keyword in layer.name() for keyword in ['Точка', 'Линии', 'Все_крайние_точки', 'Изохрона']):
            layer_node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
            if layer_node:
                print(f"   {layer.name()}: {layer.featureCount()} объектов")
                layer_count += 1
    
    print(f"\n📊 Итого создано слоев: {layer_count}")

# Запускаем полный цикл
print("\n🚀 Запуск полного цикла создания изохрон...")
full_isochrone_pipeline()
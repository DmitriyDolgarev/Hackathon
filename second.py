print("=" * 80)
print("ПОЛНЫЙ ЦИКЛ: ЛИНИИ МАРШРУТОВ → ПОЛИГОНЫ ИЗОХРОН С НАСЕЛЕНИЕМ")
print("=" * 80)

from qgis.core import *
import processing
import math
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

# Координаты ИрНИТУ
LON = 104.261370
LAT = 52.262468

def find_roads_layer():
    """Находит слой с дорогами"""
    
    print("\n🔍 Поиск слоя с дорогами...")
    
    # Список возможных имен слоев с дорогами
    possible_names = [
        'ispravlenny_uds'
    ]
    
    # 1. Сначала проверяем активный слой
    active_layer = iface.activeLayer()
    if active_layer and active_layer.geometryType() == QgsWkbTypes.LineGeometry:
        print(f"   Используется активный слой: {active_layer.name()}")
        return active_layer
    
    # 2. Ищем по именам
    for name in possible_names:
        layers = QgsProject.instance().mapLayersByName(name)
        if layers:
            layer = layers[0]
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.LineGeometry:
                print(f"   Найден слой по имени: {layer.name()}")
                return layer
    
    # 3. Ищем все линейные слои
    print("   Поиск среди всех линейных слоев...")
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.LineGeometry:
            print(f"   Найден линейный слой: {layer.name()}")
            return layer
    
    print("   ❌ Слой с дорогами не найден!")
    
    # Выводим список всех слоев для отладки
    print("\n   Доступные слои в проекте:")
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            geom_type = {
                QgsWkbTypes.PointGeometry: "Точки",
                QgsWkbTypes.LineGeometry: "Линии", 
                QgsWkbTypes.PolygonGeometry: "Полигоны"
            }.get(layer.geometryType(), "Неизвестно")
            
            print(f"     - {layer.name()} ({geom_type}, {layer.featureCount()} объектов)")
    
    return None

def find_population_layer():
    """Находит слой с населением (здания)"""
    
    print("\n🔍 Поиск слоя с населением...")
    
    population_layer = None
    population_field = None
    
    # 1. Пробуем найти слой по имени из скриншота
    layer_names = [
        '"Здания_насел_attract"'
    ]
    
    for layer_name in layer_names:
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                population_layer = layer
                print(f"   Найден слой по имени: {layer.name()}")
                break
    
    # 2. Если не нашли по имени, ищем все полигональные слои
    if not population_layer:
        print("   Поиск среди всех полигональных слоев...")
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                print(f"   Найден полигональный слой: {layer.name()}")
                population_layer = layer
                break
    
    if not population_layer:
        print("   ❌ Слой с зданиями не найден!")
        return None, None
    
    # 3. Находим поле с населением
    print(f"   Поиск поля с населением в слое: {population_layer.name()}")
    
    # Выводим все поля для отладки
    print(f"   Все поля слоя:")
    for i, field in enumerate(population_layer.fields()):
        print(f"     {i+1}. {field.name()} ({field.typeName()})")
    
    # Явно указываем что поле 'Насел' - это поле с населением
    # Оно есть в ваших данных, как вы показали в выводе
    if 'Насел' in [field.name() for field in population_layer.fields()]:
        population_field = 'Насел'
        print(f"   ✅ Найдено поле населения: '{population_field}'")
    else:
        # Если нет поля 'Насел', ищем альтернативы
        possible_field_names = [
            'population', 'pop', 'население', 'жители', 'people', 
            'residents', 'жильцы', 'население_здания'
        ]
        
        for field in population_layer.fields():
            field_name_lower = field.name().lower()
            for possible_name in possible_field_names:
                if possible_name in field_name_lower:
                    population_field = field.name()
                    print(f"   ✅ Найдено поле населения: '{population_field}'")
                    break
            
            if population_field:
                break
    
    # 4. Если не нашли по названию, пробуем числовые поля, НО не 'NO'!
    if not population_field:
        print("   Поиск числовых полей (кроме 'NO')...")
        for field in population_layer.fields():
            # Исключаем поле 'NO' - это номер, а не население!
            if field.name() != 'NO' and field.type() in [QVariant.Int, QVariant.Double, QVariant.LongLong]:
                population_field = field.name()
                print(f"   ⚠️  Выбрано числовое поле: '{population_field}' (не 'NO')")
                break
    
    # 5. Проверяем данные в поле
    if population_field:
        print(f"\n   Проверка данных в поле '{population_field}':")
        
        total_population = 0
        non_null_count = 0
        sample_size = min(100, population_layer.featureCount())
        
        for i, feature in enumerate(population_layer.getFeatures()):
            if i >= sample_size:
                break
                
            pop_value = feature[population_field]
            if pop_value is not None and pop_value != '':
                try:
                    pop_num = float(pop_value)
                    total_population += pop_num
                    non_null_count += 1
                except (ValueError, TypeError):
                    pass
        
        if non_null_count > 0:
            print(f"   Образец: {non_null_count} из {sample_size} объектов имеют данные")
            print(f"   Среднее население на здание: {total_population/non_null_count:.1f} чел.")
        else:
            print(f"   ⚠️  В первых {sample_size} объектах нет числовых данных")
            print(f"   Проверьте правильность выбранного поля")
    
    return population_layer, population_field

def full_isochrone_pipeline():
    """Полный цикл создания изохрон: линии → полигоны с населением"""
    
    print("🔍 Проверка данных...")
    
    # 0. Находим слой с населением
    population_layer, population_field = find_population_layer()
    
    if not population_layer or not population_field:
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЕ: Слой с населением не найден или не определено поле!")
        print("   Полигоны будут созданы БЕЗ данных о населении.")
        print("   Для расчета населения убедитесь, что слой '3дания_Hace_n_attract' загружен.")
        print("   Продолжаем расчет...\n")
        has_population_data = False
    else:
        has_population_data = True
        print(f"\n✅ Данные о населении: Слой '{population_layer.name()}', поле '{population_field}'")
    
    # 1. Находим слой дорог
    roads = find_roads_layer()
    if not roads:
        print("❌ Не удалось найти слой с дорогами!")
        print("   Убедитесь, что слой 'ispravlenny_uds' или другой слой с дорогами загружен.")
        return
    
    print(f"\n✅ Слой дорог: {roads.name()} ({roads.featureCount()} сегментов)")
    
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
        if any(keyword in layer.name() for keyword in ['Линии', 'Полигон', 'Изохрона', 'Точка', 'Все_крайние_точки']):
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
    print(f"\n" + "-" * 50)
    print("ЭТАП 1: СОЗДАНИЕ ЛИНИЙ МАРШРУТОВ")
    print("-" * 50)
    
    line_layers = []

    end_points_five = []
    end_points_ten = []
    end_points_fiveteen = []
    
    for time_min in time_intervals:
        print(f"\n⏱️  {time_min} минут:")
        
        distance_m = (speed_kmh * 1000 / 3600) * (time_min * 60)
        print(f"   Расстояние: {distance_m:.0f} м")
        
        # Пробуем алгоритм
        print(f"   Создание линий...")
        
        params = {
            'INPUT': roads,
            'START_POINTS': point_layer,
            'TRAVEL_COST': distance_m,
            'STRATEGY': 0,  # 0 = Shortest distance
            'TOLERANCE': 100,  # Увеличил для надежности
            'OUTPUT_LINES': 'memory:',
            'OUTPUT': 'memory:'
        }
        
        try:
            # Пробуем разные алгоритмы
            algorithms = ['qgis:serviceareafromlayer', 'native:serviceareafrompoint']
            
            lines_created = False
            for algorithm in algorithms:
                try:
                    print(f"   Пробую алгоритм: {algorithm}")
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
                            print(f"   Извлечение КРАЙНИХ точек маршрутов...")
                            
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
                            
                            print(f"   Сегментов: {total_segments}, КРАЙНИХ точек добавлено: {end_points_added}")
                            
                            lines_created = True
                            break  # Выходим из цикла алгоритмов
                            
                except Exception as e:
                    print(f"   ❌ Алгоритм {algorithm} не сработал: {str(e)[:100]}")
                    continue
            
            if not lines_created:
                print(f"   ⚠️  Не удалось создать линии, пропускаю")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    print(f"\n📊 ИТОГО собрано КРАЙНИХ точек:")
    print(f"   5 минут: {len(end_points_five)} точек")
    print(f"   10 минут: {len(end_points_ten)} точек")
    print(f"   15 минут: {len(end_points_fiveteen)} точек")

    # 7. СОЗДАЕМ ПОЛИГОНЫ ИЗ КРАЙНИХ ТОЧЕК С РАСЧЕТОМ НАСЕЛЕНИЯ
    print(f"\n" + "=" * 50)
    print("ЭТАП 2: СОЗДАНИЕ ПОЛИГОНОВ ИЗ КРАЙНИХ ТОЧЕК")
    print("=" * 50)

    def calculate_population_in_polygon(polygon_geom, polygon_layer_crs):
        """Оптимизированный расчет населения внутри полигона - БЕЗ изменения исходной геометрии"""
        
        total_population = 0
        buildings_count = 0
        
        if not has_population_data or not population_layer:
            print("   ⚠️  Нет данных о населении для расчета")
            return 0, 0
        
        print(f"   Оптимизированный расчет населения...")
        
        try:
            # 1. Определяем поле для расчета населения
            population_field = 'Насел'
            field_names = [field.name() for field in population_layer.fields()]
            
            if population_field not in field_names:
                for alt_field in ['att_mn', 'att_nig', 'population', 'pop']:
                    if alt_field in field_names:
                        population_field = alt_field
                        break
            
            print(f"   Используемое поле: '{population_field}'")
            
            # 2. СОЗДАЕМ КОПИЮ геометрии для преобразования CRS
            polygon_geom_for_calculation = QgsGeometry(polygon_geom)
            polygon_crs = polygon_layer_crs
            buildings_crs = population_layer.crs()
            
            if polygon_crs.authid() != buildings_crs.authid():
                print(f"   Преобразование CRS копии полигона...")
                transform = QgsCoordinateTransform(polygon_crs, buildings_crs, QgsProject.instance())
                polygon_geom_for_calculation.transform(transform)  # Преобразуем КОПИЮ
            
            # 3. СОЗДАЕМ ПРОСТРАНСТВЕННЫЙ ИНДЕКС
            print(f"   Создание пространственного индекса зданий...")
            
            # ПРАВИЛЬНЫЙ способ создания индекса
            spatial_index = QgsSpatialIndex()
            
            # Быстро добавляем все объекты в индекс
            features_list = []
            feature_ids = []
            
            print(f"   Индексация {population_layer.featureCount()} зданий...")
            
            # Используем итератор с прогрессом
            for i, feature in enumerate(population_layer.getFeatures()):
                if feature.geometry():
                    spatial_index.addFeature(feature)
                    features_list.append(feature)
                    feature_ids.append(feature.id())
                
                if i % 5000 == 0 and i > 0:
                    print(f"   Проиндексировано {i} зданий...")
            
            print(f"   Индекс создан. Всего в индексе: {len(feature_ids)} зданий")
            
            # 4. Находим здания в bounding box полигона
            print(f"   Поиск зданий в bounding box полигона...")
            bbox = polygon_geom_for_calculation.boundingBox()
            
            print(f"   Bounding box полигона:")
            print(f"     Xmin: {bbox.xMinimum():.2f}, Ymin: {bbox.yMinimum():.2f}")
            print(f"     Xmax: {bbox.xMaximum():.2f}, Ymax: {bbox.yMaximum():.2f}")
            
            # Добавляем буфер 5 метров для граничных случаев
            buffer_distance = 5
            bbox_buffered = QgsRectangle(
                bbox.xMinimum() - buffer_distance,
                bbox.yMinimum() - buffer_distance,
                bbox.xMaximum() + buffer_distance,
                bbox.yMaximum() + buffer_distance
            )
            
            # Используем индекс для поиска
            candidate_ids = spatial_index.intersects(bbox_buffered)
            print(f"   Найдено кандидатов в BBox: {len(candidate_ids)} зданий")
            
            if len(candidate_ids) == 0:
                print(f"   ⚠️  В BBox полигона нет зданий!")
                
                # Проверим центр полигона
                center = polygon_geom_for_calculation.centroid().asPoint()
                print(f"   Центр полигона: X={center.x():.2f}, Y={center.y():.2f}")
                
                # Создаем маленький bbox вокруг центра для проверки
                test_bbox = QgsRectangle(
                    center.x() - 100, center.y() - 100,
                    center.x() + 100, center.y() + 100
                )
                
                test_ids = spatial_index.intersects(test_bbox)
                print(f"   Зданий в радиусе 100м от центра: {len(test_ids)}")
                
                if len(test_ids) > 0:
                    # Проверим координаты найденных зданий
                    print(f"   Проверка координат найденных зданий:")
                    for i, fid in enumerate(test_ids[:3]):
                        # Находим объект по ID
                        request = QgsFeatureRequest().setFilterFid(fid)
                        feature = next(population_layer.getFeatures(request))
                        geom = feature.geometry()
                        if geom:
                            pt = geom.centroid().asPoint()
                            print(f"     Здание {fid}: X={pt.x():.2f}, Y={pt.y():.2f}")
                
                return 0, 0
            
            # 5. ПРЕДВАРИТЕЛЬНАЯ ФИЛЬТРАЦИЯ: создаем словарь для быстрого доступа
            print(f"   Подготовка данных для обработки...")
            
            # Создаем словарь объектов по ID для быстрого доступа
            features_dict = {}
            
            # Используем QgsFeatureRequest для загрузки только нужных объектов
            request = QgsFeatureRequest()
            request.setFilterFids(list(candidate_ids))
            request.setSubsetOfAttributes([population_field], population_layer.fields())
            
            for feature in population_layer.getFeatures(request):
                features_dict[feature.id()] = feature
            
            print(f"   Загружено {len(features_dict)} объектов для обработки")
            
            # 6. ТОЧНАЯ ПРОВЕРКА пересечений
            print(f"   Точная проверка пересечений...")
            
            inside_count = 0
            partial_count = 0
            processed = 0
            
            # Для отладки выведем первые несколько значений населения
            print(f"   Примеры значений поля '{population_field}':")
            sample_count = 0
            for fid in list(candidate_ids)[:5]:
                if fid in features_dict:
                    feature = features_dict[fid]
                    pop_value = feature[population_field]
                    print(f"     Здание {fid}: {population_field} = {pop_value} (тип: {type(pop_value)})")
                    sample_count += 1
            
            # Основной цикл обработки
            for fid in candidate_ids:
                if fid not in features_dict:
                    continue
                    
                feature = features_dict[fid]
                building_geom = feature.geometry()
                
                if building_geom is None or building_geom.isEmpty():
                    continue
                
                # Проверяем пересечение
                if building_geom.intersects(polygon_geom_for_calculation):
                    # Получаем значение населения
                    pop_value = feature[population_field]
                    pop_num = 0
                    
                    # Преобразуем в число
                    if pop_value is not None and str(pop_value).strip() != '':
                        try:
                            pop_str = str(pop_value).replace(',', '.').strip()
                            pop_num = float(pop_str) if pop_str else 0
                        except (ValueError, TypeError):
                            pop_num = 0
                    
                    # Если есть население, считаем
                    if pop_num > 0:
                        processed += 1
                        
                        # Проверяем, полностью ли внутри
                        if building_geom.within(polygon_geom_for_calculation):
                            # Полностью внутри
                            total_population += pop_num
                            buildings_count += 1
                            inside_count += 1
                        else:
                            # Частично внутри
                            intersection = building_geom.intersection(polygon_geom_for_calculation)
                            if intersection and not intersection.isEmpty():
                                building_area = building_geom.area()
                                if building_area > 0:
                                    intersection_area = intersection.area()
                                    proportion = intersection_area / building_area
                                    
                                    # Учитываем если больше 5%
                                    if proportion > 0.05:
                                        total_population += pop_num * proportion
                                        buildings_count += proportion
                                        partial_count += 1
                        
                        # Выводим прогресс
                        if processed % 50 == 0:
                            print(f"   Обработано {processed}/{len(candidate_ids)} зданий...")
            
            # 7. ВЫВОД РЕЗУЛЬТАТОВ
            print(f"\n   📊 РЕЗУЛЬТАТЫ РАСЧЕТА:")
            print(f"     Всего кандидатов: {len(candidate_ids)}")
            print(f"     Обработано с населением: {processed}")
            print(f"     Полностью внутри: {inside_count} зданий")
            print(f"     Частично внутри: {partial_count} зданий")
            print(f"     Общее население: {total_population:.0f} чел.")
            
            # Дополнительная диагностика если население = 0
            if total_population == 0 and processed > 0:
                print(f"\n   ⚠️  Диагностика: обработано {processed} зданий, но население = 0")
                print(f"     Проверяю значения населения...")
                
                # Проверяем значения в первых 10 пересекающихся зданиях
                check_count = 0
                for fid in candidate_ids:
                    if fid in features_dict:
                        feature = features_dict[fid]
                        building_geom = feature.geometry()
                        
                        if building_geom and building_geom.intersects(polygon_geom_for_calculation):
                            pop_value = feature[population_field]
                            print(f"       Здание {fid}: {population_field} = {pop_value}")
                            check_count += 1
                            
                            if check_count >= 10:
                                break
            
            return total_population, buildings_count
        
        except Exception as e:
            print(f"   ❌ Ошибка при расчете: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0

    def create_polygon_from_end_points(points, name, color, border_color):
        """Создает ЕДИНЫЙ полигон из списка КРАЙНИХ точек с населением"""
        
        if len(points) < 3:
            print(f"   ❌ Недостаточно КРАЙНИХ точек для полигона {name} ({len(points)} точек)")
            return None
        
        print(f"\n   Создание полигона {name} из {len(points)} крайних точек...")
        
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
        print(f"   Создание выпуклой оболочки...")
        
        try:
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
                print(f"   ❌ Не удалось создать выпуклой оболочки для {name}")
                return None
            
        except Exception as e:
            print(f"   ❌ Ошибка при создании выпуклой оболочки: {e}")
            return None
        
        # 3. Получаем геометрию полигона
        convex_features = list(convex_layer.getFeatures())
        polygon_geom = convex_features[0].geometry()
        
        # 4. СОЗДАЕМ КОПИЮ ГЕОМЕТРИИ для расчета населения
        # Это критически важно, чтобы не изменять исходную геометрию!
        polygon_geom_for_population = QgsGeometry(polygon_geom)  # Создаем копию
        
        # Проверяем и исправляем геометрию (для обеих копий)
        if not polygon_geom.isGeosValid():
            print(f"   Геометрия требует исправления...")
            polygon_geom = polygon_geom.makeValid()
            polygon_geom_for_population = QgsGeometry(polygon_geom)  # Копируем исправленную
        
        # 5. Рассчитываем население НА КОПИИ геометрии
        print(f"   Расчет населения...")
        total_population, buildings_count = calculate_population_in_polygon(polygon_geom_for_population, roads_crs)
        
        # 6. Создаем финальный полигонный слой с ИСХОДНОЙ геометрией
        polygon_layer = QgsVectorLayer(f"Polygon?crs={roads_crs.authid()}", name, "memory")
        polygon_provider = polygon_layer.dataProvider()
        
        # ДОБАВЛЯЕМ ПОЛЯ
        polygon_provider.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("name", QVariant.String),
            QgsField("time_min", QVariant.Int),
            QgsField("points_count", QVariant.Int),
            QgsField("area_m2", QVariant.Double),
            QgsField("buildings_count", QVariant.Double),
            QgsField("population", QVariant.Double),
            QgsField("density_ha", QVariant.Double)
        ])
        polygon_layer.updateFields()
        
        # Рассчитываем площадь ИСХОДНОЙ геометрии
        area_calc = QgsDistanceArea()
        area_calc.setSourceCrs(roads_crs, QgsProject.instance().transformContext())
        area_calc.setEllipsoid(roads_crs.ellipsoidAcronym())
        area_m2 = area_calc.measureArea(polygon_geom)  # Используем ИСХОДНУЮ геометрию
        
        # Рассчитываем плотность
        area_ha = area_m2 / 10000
        density_ha = total_population / area_ha if area_ha > 0 else 0
        
        # Определяем время по имени
        time_min = 5 if "5мин" in name else (10 if "10мин" in name else 15)
        
        # Создаем объект с ИСХОДНОЙ геометрией
        feat = QgsFeature()
        feat.setGeometry(polygon_geom)  # Используем ИСХОДНУЮ геометрию
        feat.setAttributes([
            1,
            name,
            time_min,
            len(points),
            area_m2,
            buildings_count,
            total_population,
            density_ha
        ])
        polygon_provider.addFeatures([feat])
        
        polygon_layer.updateExtents()
        
        # 7. Применяем стиль
        symbol = QgsFillSymbol.createSimple({
            'color': color,
            'color_border': border_color,
            'width_border': '1.5',
            'style': 'solid'
        })
        polygon_layer.renderer().setSymbol(symbol)
        
        # 8. Добавляем подписи
        label_settings = QgsPalLayerSettings()
        if has_population_data:
            label_settings.fieldName = '''
                concat(
                    "name",
                    '\n',
                    round("area_m2" / 10000, 2), ' га',
                    '\n',
                    round("population"), ' чел.',
                    '\n',
                    round("density_ha", 1), ' чел/га'
                )
            '''
        else:
            label_settings.fieldName = '''
                concat(
                    "name",
                    '\n',
                    round("area_m2" / 10000, 2), ' га'
                )
            '''
        label_settings.isExpression = True
        
        text_format = QgsTextFormat()
        text_format.setSize(9)
        text_format.setColor(QColor("white"))
        text_format.setFont(QFont("Arial", 9, QFont.Bold))
        text_format.buffer().setEnabled(True)
        text_format.buffer().setColor(QColor("black"))
        text_format.buffer().setSize(2)
        
        label_settings.setFormat(text_format)
        label_settings.enabled = True
        
        layer_labeling = QgsVectorLayerSimpleLabeling(label_settings)
        polygon_layer.setLabeling(layer_labeling)
        polygon_layer.setLabelsEnabled(True)
        
        print(f"   ✅ Полигон {name} создан:")
        print(f"      Площадь: {area_m2:.0f} м² ({area_ha:.2f} га)")
        if has_population_data:
            print(f"      Здания: {buildings_count:.1f} шт.")
            print(f"      Население: {total_population:.0f} чел.")
            print(f"      Плотность: {density_ha:.1f} чел/га")
        
        return polygon_layer

    # Создаем полигоны из КРАЙНИХ точек с населением
    polygon_layers = []
    population_summary = []

    # Создаем полигоны в порядке от большего к меньшему (чтобы перекрывались правильно)
    # 3. Полигон для 15 минут
    if len(end_points_fiveteen) >= 3:
        print("\n" + "="*60)
        print("Создание полигона для 15 минут...")
        polygon_fifteen = create_polygon_from_end_points(
            end_points_fiveteen,
            "Изохрона_15мин",
            "255,0,0,100",       # Красный с прозрачностью
            "200,0,0"            # Темно-красная граница
        )
        if polygon_fifteen:
            QgsProject.instance().addMapLayer(polygon_fifteen)
            polygon_layers.append(polygon_fifteen)
            
            # Сохраняем данные для итогового отчета
            features = list(polygon_fifteen.getFeatures())
            if features:
                pop_data = features[0].attributes()
                population_summary.append({
                    'time': 15,
                    'population': pop_data[6],  # population field
                    'area_ha': pop_data[4] / 10000,  # area_m2 to hectares
                    'density': pop_data[7]  # density_ha
                })
    else:
        print("❌ Недостаточно КРАЙНИХ точек для полигона 15 минут")

    # 2. Полигон для 10 минут
    if len(end_points_ten) >= 3:
        print("\n" + "="*60)
        print("Создание полигона для 10 минут...")
        polygon_ten = create_polygon_from_end_points(
            end_points_ten,
            "Изохрона_10мин",
            "255,165,0,80",    # Оранжевый с прозрачностью
            "255,100,0"         # Темно-оранжевая граница
        )
        if polygon_ten:
            QgsProject.instance().addMapLayer(polygon_ten)
            polygon_layers.append(polygon_ten)
            
            # Сохраняем данные для итогового отчета
            features = list(polygon_ten.getFeatures())
            if features:
                pop_data = features[0].attributes()
                population_summary.append({
                    'time': 10,
                    'population': pop_data[6],  # population field
                    'area_ha': pop_data[4] / 10000,  # area_m2 to hectares
                    'density': pop_data[7]  # density_ha
                })
    else:
        print("❌ Недостаточно КРАЙНИХ точек для полигона 10 минут")

    # 1. Полигон для 5 минут
    if len(end_points_five) >= 3:
        print("\n" + "="*60)
        print("Создание полигона для 5 минут...")
        polygon_five = create_polygon_from_end_points(
            end_points_five,
            "Изохрона_5мин",
            "255,255,0,60",      # Желтый с прозрачностью
            "255,200,0"         # Оранжевая граница
        )
        if polygon_five:
            QgsProject.instance().addMapLayer(polygon_five)
            polygon_layers.append(polygon_five)
            
            # Сохраняем данные для итогового отчета
            features = list(polygon_five.getFeatures())
            if features:
                pop_data = features[0].attributes()
                population_summary.append({
                    'time': 5,
                    'population': pop_data[6],  # population field
                    'area_ha': pop_data[4] / 10000,  # area_m2 to hectares
                    'density': pop_data[7]  # density_ha
                })
    else:
        print("❌ Недостаточно КРАЙНИХ точек для полигона 5 минут")

    # 8. ВЫВОД ИТОГОВОЙ СТАТИСТИКИ
    print(f"\n" + "="*80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("="*80)
    
    if has_population_data and population_summary:
        print("\n📊 Сводная таблица по изохронам:")
        print("-" * 70)
        print(f"{'Время (мин)':<12} {'Площадь (га)':<15} {'Население (чел)':<18} {'Плотность (чел/га)':<20}")
        print("-" * 70)
        
        total_population = 0
        total_area = 0
        
        for summary in sorted(population_summary, key=lambda x: x['time']):
            print(f"{summary['time']:<12} {summary['area_ha']:<15.2f} {summary['population']:<18.0f} {summary['density']:<20.1f}")
            total_population += summary['population']
            total_area += summary['area_ha']
        
        print("-" * 70)
        print(f"{'ИТОГО':<12} {total_area:<15.2f} {total_population:<18.0f}")
    
    # 9. Финальные действия
    print(f"\n" + "-" * 40)
    print("ЭТАП 3: ЗАВЕРШЕНИЕ")
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
    
    print("\n✅ РАСЧЕТ ЗАВЕРШЕН:")
    print(f"   Точка: {LAT:.6f}°N, {LON:.6f}°E")
    print(f"   Скорость: {speed_kmh} км/ч")
    print(f"   Времена: {', '.join(str(t) for t in time_intervals)} мин")
    
    if has_population_data:
        print(f"   Данные о населении: ЕСТЬ")
    else:
        print(f"   Данные о населении: НЕТ")
    
    print(f"\n🎉 Создано полигонов: {len(polygon_layers)}")
    print(f"💾 Для сохранения результатов используйте:")
    print(f"   ПКМ по слою → Export → Save Features As...")
    print(f"   Форматы: GeoJSON, Shapefile, GPKG")

# Запускаем полный цикл
print("\n🚀 Запуск полного цикла создания изохрон с населением...")
print("📝 Перед запуском убедитесь, что:")
print("   1. Слой 'ispravlenny_uds' загружен (дороги)")
print("   2. Слой '3дания_Hace_n_attract' загружен (здания с населением)")
print("=" * 80)
full_isochrone_pipeline()
